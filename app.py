import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "chave_secreta_cambuci_2026"
DATABASE = "escola.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS alunos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, instrumento TEXT NOT NULL, telefone TEXT, data_matricula TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS professores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, especialidade TEXT NOT NULL, telefone TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, categoria TEXT NOT NULL, preco REAL NOT NULL, estoque INTEGER NOT NULL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, categoria_fluxo TEXT NOT NULL, descricao TEXT NOT NULL, valor REAL NOT NULL, data TEXT NOT NULL)')
        cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL)')
        
        try:
            cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('admin', 'admin123', 'administrador')")
            cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('caixa', 'caixa123', 'caixa')")
            cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha, perfil) VALUES ('secretaria', 'sec123', 'secretaria')")
        except sqlite3.Error:
            pass
        conn.commit()
        conn.close()

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM usuarios WHERE usuario = ? AND senha = ?', (usuario, senha)).fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            session['usuario'] = user['usuario']
            session['perfil'] = user['perfil']
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    alunos = conn.execute('SELECT * FROM alunos').fetchall()
    professores = conn.execute('SELECT * FROM professores').fetchall()
    produtos = conn.execute('SELECT * FROM produtos').fetchall()
    movimentacoes = conn.execute('SELECT * FROM financeiro ORDER BY id DESC').fetchall()
    total_entradas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='entrada'").fetchone()[0] or 0.0
    total_saidas = conn.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='saida'").fetchone()[0] or 0.0
    saldo_caixa = total_entradas - total_saidas
    conn.close()
    return render_template('index.html', alunos=alunos, professores=professores, produtos=produtos, movimentacoes=movimentacoes, total_entradas=total_entradas, total_saidas=total_saidas, saldo_caixa=saldo_caixa)

@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    nome, instrumento, telefone = request.form.get('nome'), request.form.get('instrumento'), request.form.get('telefone')
    conn = get_db_connection()
    conn.execute('INSERT INTO alunos (nome, instrumento, telefone, data_matricula) VALUES (?, ?, ?, ?)', (nome, instrumento, telefone, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_professor', methods=['POST'])
def cadastrar_professor():
    nome, especialidade, telefone = request.form.get('nome'), request.form.get('especialidade'), request.form.get('telefone')
    conn = get_db_connection()
    conn.execute('INSERT INTO professores (nome, especialidade, telefone) VALUES (?, ?, ?)', (nome, especialidade, telefone))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/registrar_financeiro', methods=['POST'])
def registrar_financeiro():
    tipo, categoria, descricao, valor = request.form.get('tipo'), request.form.get('categoria_fluxo'), request.form.get('descricao'), float(request.form.get('valor') or 0)
    conn = get_db_connection()
    conn.execute('INSERT INTO financeiro (tipo, categoria_fluxo, descricao, valor, data) VALUES (?, ?, ?, ?, ?)', (tipo, categoria, descricao, valor, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/cadastrar_produto', methods=['POST'])
def cadastrar_produto():
    nome, categoria, preco, estoque = request.form.get('nome'), request.form.get('categoria'), float(request.form.get('preco') or 0), int(request.form.get('estoque') or 0)
    conn = get_db_connection()
    conn.execute('INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (?, ?, ?, ?)', (nome, categoria, preco, estoque))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
