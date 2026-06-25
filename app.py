from flask import Flask, request, jsonify, render_template
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)

def get_conn():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        dbname=os.environ.get('DB_NAME'),
        port=5432
    )

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contas (
            id SERIAL PRIMARY KEY,
            titular VARCHAR(100) NOT NULL,
            cpf VARCHAR(11) UNIQUE NOT NULL,
            saldo NUMERIC(10,2) DEFAULT 0.00,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id SERIAL PRIMARY KEY,
            conta_id INTEGER REFERENCES contas(id),
            tipo VARCHAR(30) NOT NULL,
            valor NUMERIC(10,2) NOT NULL,
            descricao TEXT,
            realizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# Inicializa o banco ao subir
with app.app_context():
    import time
    for i in range(10):
        try:
            init_db()
            print("Banco inicializado com sucesso!")
            break
        except Exception as e:
            print(f"Aguardando banco... tentativa {i+1}: {e}")
            time.sleep(3)

# ──────────────────────────────────────────
# Página principal
# ──────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ──────────────────────────────────────────
# CONTAS
# ──────────────────────────────────────────
@app.route('/api/contas', methods=['GET'])
def listar_contas():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM contas ORDER BY criado_em DESC")
    contas = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(c) for c in contas])

@app.route('/api/contas', methods=['POST'])
def criar_conta():
    data = request.get_json()
    titular = data.get('titular', '').strip()
    cpf = data.get('cpf', '').replace('.','').replace('-','').strip()
    saldo_inicial = float(data.get('saldoInicial', 0))

    if not titular or not cpf:
        return jsonify({'erro': 'Titular e CPF são obrigatórios.'}), 400

    if not cpf.isdigit():
        return jsonify({'erro': 'CPF deve conter apenas números.'}), 400

    if len(cpf) != 11:
        return jsonify({'erro': 'CPF deve possuir 11 dígitos.'}), 400
    
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO contas (titular, cpf, saldo) VALUES (%s, %s, %s) RETURNING *",
            (titular, cpf, saldo_inicial)
        )
        conta = dict(cur.fetchone())
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'conta': conta}), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({'erro': 'CPF já cadastrado.'}), 409
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
@app.route('/api/contas/<int:id>', methods=['DELETE'])
def excluir_conta(id):

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:

        cur.execute(
            "SELECT * FROM contas WHERE id = %s",
            (id,)
        )

        conta = cur.fetchone()

        if not conta:
            return jsonify({
                'erro': 'Conta não encontrada.'
            }), 404

        if float(conta['saldo']) != 0:
            return jsonify({
                'erro': 'Só é possível excluir contas com saldo zerado.'
            }), 400

        cur.execute(
            "DELETE FROM transacoes WHERE conta_id = %s",
            (id,)
        )

        cur.execute(
            "DELETE FROM contas WHERE id = %s",
            (id,)
        )

        conn.commit()

        return jsonify({
            'sucesso': True
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            'erro': str(e)
        }), 500

    finally:
        cur.close()
        conn.close()
# ──────────────────────────────────────────
# TRANSAÇÕES
# ──────────────────────────────────────────
@app.route('/api/transacoes', methods=['GET'])
def listar_transacoes():
    conta_id = request.args.get('conta_id')
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if conta_id:
        cur.execute("""
            SELECT t.*, c.titular FROM transacoes t
            JOIN contas c ON t.conta_id = c.id
            WHERE t.conta_id = %s ORDER BY t.realizado_em DESC LIMIT 50
        """, (conta_id,))
    else:
        cur.execute("""
            SELECT t.*, c.titular FROM transacoes t
            JOIN contas c ON t.conta_id = c.id
            ORDER BY t.realizado_em DESC LIMIT 50
        """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(rows)

@app.route('/api/transacoes', methods=['POST'])
def realizar_transacao():
    data = request.get_json()
    conta_id = data.get('conta_id')
    tipo = data.get('tipo')
    valor = float(data.get('valor', 0))
    descricao = data.get('descricao', '')
    conta_destino_id = data.get('conta_destino_id')

    if not conta_id or not tipo or valor <= 0:
        return jsonify({'erro': 'Dados inválidos.'}), 400

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        conn.autocommit = False

        cur.execute("SELECT * FROM contas WHERE id = %s FOR UPDATE", (conta_id,))
        conta = cur.fetchone()
        if not conta:
            conn.rollback()
            return jsonify({'erro': 'Conta não encontrada.'}), 404

        if tipo == 'deposito':
            cur.execute("UPDATE contas SET saldo = saldo + %s WHERE id = %s", (valor, conta_id))
            cur.execute(
                "INSERT INTO transacoes (conta_id, tipo, valor, descricao) VALUES (%s, %s, %s, %s)",
                (conta_id, 'deposito', valor, descricao or 'Depósito')
            )

        elif tipo == 'saque':
            if float(conta['saldo']) < valor:
                conn.rollback()
                return jsonify({'erro': 'Saldo insuficiente.'}), 400
            cur.execute("UPDATE contas SET saldo = saldo - %s WHERE id = %s", (valor, conta_id))
            cur.execute(
                "INSERT INTO transacoes (conta_id, tipo, valor, descricao) VALUES (%s, %s, %s, %s)",
                (conta_id, 'saque', valor, descricao or 'Saque')
            )

        elif tipo == 'transferencia':
            if not conta_destino_id:
                conn.rollback()
                return jsonify({'erro': 'Conta destino obrigatória.'}), 400
            if float(conta['saldo']) < valor:
                conn.rollback()
                return jsonify({'erro': 'Saldo insuficiente.'}), 400
            cur.execute("SELECT * FROM contas WHERE id = %s FOR UPDATE", (conta_destino_id,))
            destino = cur.fetchone()
            if not destino:
                conn.rollback()
                return jsonify({'erro': 'Conta destino não encontrada.'}), 404

            cur.execute("UPDATE contas SET saldo = saldo - %s WHERE id = %s", (valor, conta_id))
            cur.execute("UPDATE contas SET saldo = saldo + %s WHERE id = %s", (valor, conta_destino_id))
            cur.execute(
                "INSERT INTO transacoes (conta_id, tipo, valor, descricao) VALUES (%s, %s, %s, %s)",
                (conta_id, 'transferencia_saida', valor, f'Transferência para conta #{conta_destino_id}')
            )
            cur.execute(
                "INSERT INTO transacoes (conta_id, tipo, valor, descricao) VALUES (%s, %s, %s, %s)",
                (conta_destino_id, 'transferencia_entrada', valor, f'Transferência recebida da conta #{conta_id}')
            )
        else:
            conn.rollback()
            return jsonify({'erro': 'Tipo inválido.'}), 400

        conn.commit()

        cur.execute("SELECT * FROM contas WHERE id = %s", (conta_id,))
        conta_atualizada = dict(cur.fetchone())
        return jsonify({'sucesso': True, 'conta': conta_atualizada})

    except Exception as e:
        conn.rollback()
        return jsonify({'erro': str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)
