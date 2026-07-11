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

# --- MÓDULOS DE ESTÚDIO ATUALIZADOS ---
class AgendamentoEstudio(db.Model):
    __tablename__ = 'agendamentos_estudio'
    id = db.Column(db.Integer, primary_key=True)
    tipo_estudio = db.Column(db.String(50), nullable=False) # Gravação, Videoclipe ou Ensaio
    
    # Dados completos do cliente/artista
    nome_cliente = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    endereco_completo = db.Column(db.Text, nullable=False)
    comprovante_endereco = db.Column(db.String(255))
    
    # Dados do Agendamento
    data_agendamento = db.Column(db.Date, nullable=False)
    horario_inicio = db.Column(db.Time, nullable=False)
    horario_final = db.Column(db.Time, nullable=False)
    
    # Controle Operacional e Financeiro
    nome_tecnico = db.Column(db.String(100), nullable=False)
    status_pagamento = db.Column(db.String(20), nullable=False, default='A Pagar')
    status_trabalho = db.Column(db.String(20), nullable=False, default='Agendado')
    
    observacoes = db.Column(db.Text)
    lancamento_caixa_id = db.Column(db.Integer, db.ForeignKey('lancamentos_caixa.id'), nullable=True)

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
