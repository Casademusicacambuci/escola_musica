from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
import sqlite3
import csv
import io

app = Flask(__name__)
app.secret_key = "chave_secreta_cambuci"

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Tabela de Fornecedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT,
            telefone TEXT,
            email TEXT,
            produto_servico TEXT
        )
    ''')
    
    # Tabela de Funcionários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cargo TEXT NOT NULL,
            telefone TEXT,
            email TEXT,
            salario REAL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- SIMULADOR DE ALTERNAÇÃO DE PERFIL ---
@app.route('/alternar_usuario/<perfil_selecionado>')
def alternar_usuario(perfil_selecionado):
    if perfil_selecionado in ['administrador', 'operador_caixa']:
        session['perfil'] = perfil_selecionado
        flash(f"Perfil alterado para {perfil_selecionado.replace('_', ' ').title()}")
    return redirect(url_for('index'))

# --- ROTA INICIAL ---
@app.route('/')
def index():
    # Define administrador como padrão caso não exista sessão ativa
    if 'perfil' not in session:
        session['perfil'] = 'administrador'
        
    perfil_atual = session['perfil']
    
    conn = get_db_connection()
    fornecedores = conn.execute('SELECT * FROM fornecedores').fetchall()
    funcionarios = conn.execute('SELECT * FROM funcionarios').fetchall()
    conn.close()
    
    return render_template(
        'index.html', 
        fornecedores=fornecedores, 
        funcionarios=funcionarios,
        nome_usuario="Deni Miller",
        perfil=perfil_atual,
        total_entradas=0.0,
        total_saidas=0.0,
        saldo_caixa=0.0,
        movimentacoes=[],
        agendamentos=[]
    )

# --- ROTAS DE ESTÚDIO & FINANCEIRO (PLACEHOLDERS EVITANDO ERROS 404) ---
@app.route('/agendar_studio', methods=['POST'])
def agendar_studio():
    flash('Agendamento simulado com sucesso!')
    return redirect(url_for('index'))

@app.route('/atualizar_status_studio/<int:id>', methods=['POST'])
def atualizar_status_studio(id):
    flash('Status do estúdio atualizado!')
    return redirect(url_for('index'))

@app.route('/lancar', methods=['POST'])
def lancar():
    flash('Movimentação financeira lançada com sucesso!')
    return redirect(url_for('index'))

@app.route('/excluir/<int:id>')
def excluir_movimentacao(id):
    flash('Lançamento excluído!')
    return redirect(url_for('index'))

# --- CRUD FORNECEDORES (MÓDULO ADM) ---
@app.route('/admin/fornecedor/add', methods=['POST'])
def add_fornecedor():
    nome = request.form['nome']
    cnpj = request.form['cnpj']
    telefone = request.form['telefone']
    email = request.form['email']
    produto_servico = request.form['produto_servico']
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO fornecedores (nome, cnpj, telefone, email, produto_servico)
        VALUES (?, ?, ?, ?, ?)
    ''', (nome, cnpj, telefone, email, produto_servico))
    conn.commit()
    conn.close()
    flash('Fornecedor adicionado com sucesso!')
    return redirect(url_for('index'))

@app.route('/admin/fornecedor/delete/<int:id>')
def delete_fornecedor(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM fornecedores WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Fornecedor removido com sucesso!')
    return redirect(url_for('index'))

# --- CRUD FUNCIONÁRIOS (MÓDULO RH) ---
@app.route('/rh/funcionario/add', methods=['POST'])
def add_funcionario():
    nome = request.form['nome']
    cargo = request.form['cargo']
    telefone = request.form['telefone']
    email = request.form['email']
    salario = request.form['salario']
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO funcionarios (nome, cargo, telefone, email, salario)
        VALUES (?, ?, ?, ?, ?)
    ''', (nome, cargo, telefone, email, salario))
    conn.commit()
    conn.close()
    flash('Funcionário registrado no RH com sucesso!')
    return redirect(url_for('index'))

@app.route('/rh/funcionario/delete/<int:id>')
def delete_funcionario(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM funcionarios WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Funcionário removido do sistema de RH!')
    return redirect(url_for('index'))

# --- EXPORTAÇÃO PARA CSV ---
@app.route('/admin/exportar/<string:tipo>')
def exportar_csv(tipo):
    conn = get_db_connection()
    output = io.StringIO()
    writer = csv.writer(output)
    
    if tipo == 'fornecedores':
         writer.writerow(['ID', 'Nome', 'CNPJ', 'Telefone', 'Email', 'Produto/Serviço'])
         rows = conn.execute('SELECT * FROM fornecedores').fetchall()
         for row in rows:
             writer.writerow([row['id'], row['nome'], row['cnpj'], row['telefone'], row['email'], row['produto_servico']])
         filename = "fornecedores.csv"
         
    elif tipo == 'funcionarios':
         writer.writerow(['ID', 'Nome', 'Cargo', 'Telefone', 'Email', 'Salário'])
         rows = conn.execute('SELECT * FROM funcionarios').fetchall()
         for row in rows:
             writer.writerow([row['id'], row['nome'], row['cargo'], row['telefone'], row['email'], row['salario']])
         filename = "funcionarios.csv"
    else:
         writer.writerow(['Filtro de data manual simulado'])
         filename = f"exportacao_{tipo}.csv"
     
    conn.close()
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

if __name__ == '__main__':
    app.run(debug=True)
