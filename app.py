from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text  # Importante para atualizar o banco de dados
import os

from models import db, Usuario, Aluno

app = Flask(__name__)
app.secret_key = 'chave_secreta_cambuci_2026' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cambuci_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()
    
    # Atualiza o banco de dados com a nova coluna caso ela não exista
    try:
        db.session.execute(text("ALTER TABLE alunos ADD COLUMN status VARCHAR(20) DEFAULT 'Ativo'"))
        db.session.commit()
    except Exception:
        db.session.rollback() # A coluna já existe, ignora o erro
    
    admin_existente = Usuario.query.filter_by(username='admin').first()
    if not admin_existente:
        senha_criptografada = generate_password_hash('admin123')
        novo_admin = Usuario(
            username='admin', password_hash=senha_criptografada,
            nome_completo='Administrador Geral', role='admin'
        )
        db.session.add(novo_admin)
        db.session.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and check_password_hash(usuario.password_hash, password):
            session['usuario_id'] = usuario.id
            session['role'] = usuario.role
            session['nome'] = usuario.nome_completo
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha incorretos. Tente novamente.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    nome = session.get('nome')
    return render_template('dashboard.html', nome=nome, role=role)

@app.route('/secretaria/alunos', methods=['GET', 'POST'])
def gerenciar_alunos():
    if 'usuario_id' not in session or session.get('role') not in ['admin', 'secretaria']:
        flash('Acesso negado. Você não tem permissão para acessar este módulo.')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        nome = request.form.get('nome')
        rg = request.form.get('rg')
        cpf = request.form.get('cpf')
        endereco = request.form.get('endereco')
        telefone = request.form.get('telefone')
        curso = request.form.get('curso')
        status = request.form.get('status') # Puxando o novo campo
        
        arquivo = request.files.get('comprovante')
        caminho_arquivo = None
        if arquivo and arquivo.filename != '':
            extensao = arquivo.filename.split('.')[-1]
            nome_arquivo = f"comprovante_{cpf}.{extensao}"
            arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            caminho_arquivo = f"uploads/{nome_arquivo}"

        aluno_existente = Aluno.query.filter_by(cpf=cpf).first()
        if aluno_existente:
            flash('Erro: Já existe um aluno cadastrado com este CPF.')
        else:
            novo_aluno = Aluno(
                nome=nome, rg=rg, cpf=cpf, 
                endereco_completo=endereco, 
                comprovante_endereco=caminho_arquivo,
                telefone=telefone, curso=curso, status=status
            )
            db.session.add(novo_aluno)
            db.session.commit()
            flash('Aluno matriculado com sucesso!')
            return redirect(url_for('gerenciar_alunos'))

    todos_alunos = Aluno.query.order_by(Aluno.nome).all()
    return render_template('alunos.html', alunos=todos_alunos)

if __name__ == '__main__':
    app.run(debug=True)
