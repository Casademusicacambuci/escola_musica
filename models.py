from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ==========================================
# MÓDULOS DE BASE (USUÁRIOS E SECRETARIA)
# ==========================================
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nome_completo = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='caixa')
    ativo = db.Column(db.Boolean, default=True)

class Aluno(db.Model):
    __tablename__ = 'alunos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False, unique=True)
    email = db.Column(db.String(120))
    data_nascimento = db.Column(db.Date)
    nome_responsavel = db.Column(db.String(100))
    endereco_completo = db.Column(db.Text, nullable=False)
    comprovante_endereco = db.Column(db.String(255))
    telefone = db.Column(db.String(20), nullable=False)
    curso = db.Column(db.String(50), nullable=False)
    nivel = db.Column(db.String(30), nullable=False, default='Iniciante')
    data_matricula = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='Ativo')
    aulas = db.relationship('Aula', backref='aluno', lazy=True)

class Professor(db.Model):
    __tablename__ = 'professores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False, unique=True)
    email = db.Column(db.String(120))
    data_nascimento = db.Column(db.Date)
    data_inicio = db.Column(db.Date, default=datetime.utcnow)
    endereco_completo = db.Column(db.Text, nullable=False)
    comprovante_endereco = db.Column(db.String(255))
    telefone = db.Column(db.String(20), nullable=False)
    curso = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Ativo')
    aulas = db.relationship('Aula', backref='professor', lazy=True)

class Aula(db.Model):
    __tablename__ = 'aulas'
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professores.id'), nullable=False)
    instrumento = db.Column(db.String(50), nullable=False)
    data_aula = db.Column(db.Date, nullable=False)
    horario_inicio = db.Column(db.Time, nullable=False)
    horario_final = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Agendada')
    observacoes = db.Column(db.Text)

# ==========================================
# MÓDULOS DE ESTÚDIO (03, 04, 05)
# ==========================================
class AgendamentoEstudio(db.Model):
    __tablename__ = 'agendamentos_estudio'
    id = db.Column(db.Integer, primary_key=True)
    tipo_estudio = db.Column(db.String(50), nullable=False)
    nome_cliente = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    endereco_completo = db.Column(db.Text, nullable=False)
    comprovante_endereco = db.Column(db.String(255))
    data_agendamento = db.Column(db.Date, nullable=False)
    horario_inicio = db.Column(db.Time, nullable=False)
    horario_final = db.Column(db.Time, nullable=False)
    nome_tecnico = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0.0) 
    status_pagamento = db.Column(db.String(20), nullable=False, default='A Pagar')
    status_trabalho = db.Column(db.String(20), nullable=False, default='Agendado')
    observacoes = db.Column(db.Text) 

# ==========================================
# MÓDULO 01 - FINANCEIRO & BACKOFFICE (NOVOS!)
# ==========================================

class Fornecedor(db.Model):
    __tablename__ = 'fornecedores'
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(150), nullable=False)
    cnpj_cpf = db.Column(db.String(20), nullable=False, unique=True)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    categoria = db.Column(db.String(50)) # Ex: Manutenção, Limpeza, Loja
    status = db.Column(db.String(20), default='Ativo')
    contas_a_pagar = db.relationship('ContaPagar', backref='fornecedor', lazy=True)

class Funcionario(db.Model):
    __tablename__ = 'funcionarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False, unique=True)
    cargo = db.Column(db.String(50), nullable=False) # Ex: Atendente, Técnico, Limpeza
    tipo_contrato = db.Column(db.String(30)) # CLT, PJ, Freelancer
    salario_base = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Ativo')

class ContaReceber(db.Model):
    __tablename__ = 'contas_receber'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    modulo_origem = db.Column(db.String(50), nullable=False) # Ex: 'Estúdio', 'Mensalidade', 'Loja'
    origem_id = db.Column(db.Integer) # ID do agendamento ou aluno
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Pendente') # Pendente, Pago, Atrasado
    forma_pagamento = db.Column(db.String(50)) # Pix, Cartão, Dinheiro

class ContaPagar(db.Model):
    __tablename__ = 'contas_pagar'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=True)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Pendente')
    anexo_nf = db.Column(db.String(255)) # Caminho para a Nota Fiscal / Boleto salvo

class FluxoCaixa(db.Model):
    __tablename__ = 'fluxo_caixa'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False) # 'Entrada' ou 'Saída'
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    data_movimento = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

# ==========================================
# MÓDULOS DE LOJA / ESTOQUE
# ==========================================
class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    codigo_barras = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False) # Ex: Lanchonete, Instrumentos, Acessórios
    preco_custo = db.Column(db.Float, nullable=False, default=0.0)
    preco_venda = db.Column(db.Float, nullable=False)
    quantidade_estoque = db.Column(db.Integer, nullable=False, default=0)
