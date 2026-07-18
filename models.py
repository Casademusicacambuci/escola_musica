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
    valor_mensalidade = db.Column(db.Float, default=0.0) 
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

class Fornecedor(db.Model):
    __tablename__ = 'fornecedores'
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(150), nullable=False)
    cnpj_cpf = db.Column(db.String(20), nullable=False, unique=True)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    endereco_completo = db.Column(db.Text)
    chave_pix = db.Column(db.String(100))
    categoria = db.Column(db.String(50)) 
    status = db.Column(db.String(20), default='Ativo')
    contas_a_pagar = db.relationship('ContaPagar', backref='fornecedor', lazy=True)

class Funcionario(db.Model):
    __tablename__ = 'funcionarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False, unique=True)
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(20))
    data_nascimento = db.Column(db.Date)
    endereco_completo = db.Column(db.Text)
    chave_pix = db.Column(db.String(100))
    comprovante_endereco = db.Column(db.String(255))
    cargo = db.Column(db.String(50), nullable=False)
    tipo_contrato = db.Column(db.String(30)) 
    data_admissao = db.Column(db.Date, default=datetime.utcnow)
    salario_base = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Ativo')

class ContaReceber(db.Model):
    __tablename__ = 'contas_receber'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    modulo_origem = db.Column(db.String(50), nullable=False) 
    origem_id = db.Column(db.Integer) 
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Pendente') 
    forma_pagamento = db.Column(db.String(50)) 

class ContaPagar(db.Model):
    __tablename__ = 'contas_pagar'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=True)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Pendente')
    anexo_nf = db.Column(db.String(255)) 

class FluxoCaixa(db.Model):
    __tablename__ = 'fluxo_caixa'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False) 
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    data_movimento = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    codigo_barras = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    categoria = db.Column(db.String(50), nullable=False) 
    preco_custo = db.Column(db.Float, nullable=False, default=0.0)
    preco_venda = db.Column(db.Float, nullable=False)
    quantidade_estoque = db.Column(db.Integer, nullable=False, default=0)
    modalidade = db.Column(db.String(30), default='Físico')
    exibir_site = db.Column(db.Boolean, default=False)
    # ===== NOVOS CAMPOS FISCAIS PARA NF-E =====
    ncm = db.Column(db.String(20))
    cfop = db.Column(db.String(10), default='5102') 

class OrdemServico(db.Model):
    __tablename__ = 'ordens_servico'
    id = db.Column(db.Integer, primary_key=True)
    cliente_nome = db.Column(db.String(100), nullable=False)
    cliente_cpf = db.Column(db.String(14))
    cliente_telefone = db.Column(db.String(20), nullable=False)
    cliente_email = db.Column(db.String(120))
    cliente_endereco = db.Column(db.Text)
    instrumento_tipo = db.Column(db.String(50), nullable=False)
    instrumento_marca = db.Column(db.String(50))
    instrumento_modelo = db.Column(db.String(50))
    descricao_problema = db.Column(db.Text, nullable=False)
    foto_1 = db.Column(db.String(255))
    foto_2 = db.Column(db.String(255))
    foto_3 = db.Column(db.String(255))
    foto_4 = db.Column(db.String(255))
    video_link = db.Column(db.String(255)) 
    status = db.Column(db.String(50), default='Em Análise')
    solucao_sugerida = db.Column(db.Text)
    prazo_estimado = db.Column(db.String(50))
    data_entrega = db.Column(db.Date)
    valor_mao_de_obra = db.Column(db.Float, default=0.0)
    valor_pecas = db.Column(db.Float, default=0.0)
    luthier_responsavel = db.Column(db.String(100))
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)

class MovimentacaoEstoque(db.Model):
    __tablename__ = 'movimentacoes_estoque'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, nullable=True)
    nome_produto = db.Column(db.String(100), nullable=False)
    tipo_movimento = db.Column(db.String(50), nullable=False) 
    quantidade = db.Column(db.Integer, nullable=False)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    operador = db.Column(db.String(100))

class PedidoLoja(db.Model):
    __tablename__ = 'pedidos_loja'
    id = db.Column(db.Integer, primary_key=True)
    vendedor_nome = db.Column(db.String(100), nullable=False)
    cliente_nome = db.Column(db.String(100)) 
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Aberto')
    valor_total = db.Column(db.Float, default=0.0)
    itens = db.relationship('ItemPedidoLoja', backref='pedido', lazy=True, cascade='all, delete')

class ItemPedidoLoja(db.Model):
    __tablename__ = 'itens_pedido_loja'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos_loja.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    produto = db.relationship('Produto')
