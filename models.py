from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

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
    boletos = db.relationship('Boleto', backref='aluno', lazy=True)

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
    data_horario = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='agendada')

class Boleto(db.Model):
    __tablename__ = 'boletos'
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('alunos.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='gerado')
    data_pagamento = db.Column(db.DateTime)

class Recado(db.Model):
    __tablename__ = 'recados'
    id = db.Column(db.Integer, primary_key=True)
    destinatario_tipo = db.Column(db.String(20), nullable=False)
    destinatario_id = db.Column(db.Integer, nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    enviado = db.Column(db.Boolean, default=False)

class AgendamentoEstudio(db.Model):
    __tablename__ = 'agendamentos_estudio'
    id = db.Column(db.Integer, primary_key=True)
    tipo_estudio = db.Column(db.String(20), nullable=False)
    nome_artista = db.Column(db.String(100), nullable=False)
    rg = db.Column(db.String(20), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    endereco_completo = db.Column(db.Text, nullable=False)
    comprovante_endereco = db.Column(db.String(255))
    telefone = db.Column(db.String(20), nullable=False)
    horario_inicio = db.Column(db.DateTime, nullable=False)
    horario_final = db.Column(db.DateTime, nullable=False)
    status_atendimento = db.Column(db.String(20), nullable=False, default='a_pagar')
    observacoes = db.Column(db.Text)
    lancamento_caixa_id = db.Column(db.Integer, db.ForeignKey('lancamentos_caixa.id'), nullable=True)

class OrdemLuthier(db.Model):
    __tablename__ = 'ordens_luthier'
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(100), nullable=False)
    instrumento = db.Column(db.String(50), nullable=False)
    conserto_a_ser_feito = db.Column(db.Text, nullable=False)
    data_entrada = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    data_retirada = db.Column(db.Date)
    valor = db.Column(db.Float, nullable=False)
    status_pagamento = db.Column(db.String(20), nullable=False, default='a_pagar')

class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    codigo_barras = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(20), nullable=False)
    preco_venda = db.Column(db.Float, nullable=False)
    quantidade_estoque = db.Column(db.Integer, nullable=False, default=0)

class HistoricoEstoque(db.Model):
    __tablename__ = 'historico_estoque'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    tipo_movimentacao = db.Column(db.String(10), nullable=False)
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

class LancamentoCaixa(db.Model):
    __tablename__ = 'lancamentos_caixa'
    id = db.Column(db.Integer, primary_key=True)
    subdivisao = db.Column(db.String(30), nullable=False)
    tipo = db.Column(db.String(15), nullable=False, default='recebimento')
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(255))
    data_lancamento = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    agendamentos = db.relationship('AgendamentoEstudio', backref='lancamento_caixa', lazy=True)

class NotaFiscal(db.Model):
    __tablename__ = 'notas_fiscais'
    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(50), unique=True, nullable=False)
    tipo_nf = db.Column(db.String(20), nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    origem_tipo = db.Column(db.String(50))
    origem_id = db.Column(db.Integer)
