from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# Importando o banco e a tabela de Usuários lá do seu models.py
from models import db, Usuario

app = Flask(__name__)
# Chave secreta necessária para manter o usuário logado com segurança
app.secret_key = 'chave_secreta_cambuci_2026' 

# Configuração do Banco de Dados SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cambuci_crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializando o banco junto com o app
db.init_app(app)

# Cria o banco e um usuário Admin padrão se não existir
with app.app_context():
    db.create_all()
    
    # Verifica se já existe um admin. Se não, cria um para o primeiro acesso.
    admin_existente = Usuario.query.filter_by(username='admin').first()
    if not admin_existente:
        senha_criptografada = generate_password_hash('admin123')
        novo_admin = Usuario(
            username='admin',
            password_hash=senha_criptografada,
            nome_completo='Administrador Geral',
            role='admin'
        )
        db.session.add(novo_admin)
        db.session.commit()

# ==============================================================================
# SISTEMA DE LOGIN E SESSÃO
# ==============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        # Verifica se o usuário existe e se a senha bate
        if usuario and check_password_hash(usuario.password_hash, password):
            # Salva os dados na sessão (usuário está logado)
            session['usuario_id'] = usuario.id
            session['role'] = usuario.role
            session['nome'] = usuario.nome_completo
            
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha incorretos. Tente novamente.')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear() # Limpa a sessão (desloga)
    return redirect(url_for('login'))

# ==============================================================================
# ROTAS PRINCIPAIS (COM TRAVAS DE SEGURANÇA)
# ==============================================================================

@app.route('/')
def index():
    # Se já estiver logado, vai pro dashboard. Se não, vai pro login.
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    # Trava de segurança: se não tem sessão, manda pro login
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
        
    role = session.get('role')
    nome = session.get('nome')
    
    # Aqui, no futuro, faremos o redirecionamento ou exibiremos 
    # botões diferentes dependendo se o role for 'caixa', 'secretaria', 'admin', etc.
    return f"""
    <h1>Bem-vindo(a), {nome}!</h1>
    <p>Seu nível de acesso no sistema é: <strong>{role.upper()}</strong>.</p>
    <p>O sistema base está configurado e seguro!</p>
    <a href='/logout'>Sair do Sistema</a>
    """

if __name__ == '__main__':
    app.run(debug=True)
