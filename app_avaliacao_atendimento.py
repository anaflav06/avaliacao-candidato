import io
import os
import unicodedata
import re
import time
from datetime import datetime
from xml.sax.saxutils import escape

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

st.set_page_config(page_title='Avaliação Prática | Atendimento', page_icon='💬', layout='centered')

# Cada grupo é um atendimento independente; os títulos não são mostrados ao candidato.
ATENDIMENTOS = [
    [
        'Boa tarde! Tudo bem?',
        'Meu nome é Ricardo. Nunca utilizei os serviços de vocês e gostaria de tirar algumas dúvidas. Você consegue me ajudar?',
        'Preciso enviar algumas mercadorias para outra cidade, mas não sei por onde começar. O que preciso fazer?',
        'Tenho três caixas para enviar, mas uma delas está um pouco rasgada e outra está sem embalagem. Posso levar assim mesmo?',
        'Entendi. Mas são produtos frágeis e tenho medo de quebrarem durante o transporte. Como posso fazer para evitar problemas?',
        'Outra dúvida: não tenho a nota fiscal de um dos produtos. Isso seria um problema? Eu consigo enviar mesmo assim?',
        'E se a minha mercadoria quebrar ou for perdida durante o transporte? Existe algum seguro? Como funciona?',
        'Ah, lembrei de outra coisa. Também preciso enviar uma bomba de combustível usada de um carro. Ela ainda está com um pouco de gasolina. Posso colocar na caixa junto com os outros produtos?',
        'Mas é só um pouquinho de gasolina, quase nada. Se eu colocar dentro de uma sacola bem fechada, não teria problema, né?',
        'Eu trabalho o dia inteiro e tenho pouco tempo. Posso passar aí, deixar as caixas no balcão e ir embora? Depois vocês resolvem a documentação?',
        'Nossa, parece que são muitas etapas. Eu precisava resolver isso hoje porque estou com bastante pressa. Você consegue me ajudar a agilizar?',
        'Você é novo aí? Porque estou fazendo várias perguntas e algumas coisas você precisa confirmar. Você não consegue me dar uma resposta agora?',
        'Tudo bem. Se você precisar verificar essas informações, como vou receber o retorno? Você consegue me avisar por aqui?',
        'Certo, então o que você precisa de mim agora para conseguir dar andamento à minha solicitação?',
        'Tudo bem, vou separar as informações e os documentos. Muito obrigado pela atenção e pela paciência! Tenha uma ótima tarde.',
    ],
    [
        'Boa tarde! Tudo bem? Meu nome é Ricardo. Fiz um envio com vocês ontem e gostaria de saber se minha mercadoria já foi despachada. Você consegue verificar para mim?',
        'Eu deixei a mercadoria na unidade, mas não estou encontrando o comprovante do envio. Como podemos resolver isso?',
        'Preciso avisar meu cliente quando ele vai receber a mercadoria. Você consegue verificar uma previsão de entrega? É importante porque ele está me cobrando uma resposta.',
    ],
    [
        'Bom dia! Estou entrando em contato porque minha mercadoria deveria ter chegado ontem e até agora não foi entregue. Estou bastante insatisfeito, pois precisava desse material com urgência. O que aconteceu?',
        'Olha, eu entendo que imprevistos acontecem, mas paguei pelo transporte e preciso de uma solução. Não adianta apenas me dizer que vai verificar. Como vocês vão resolver meu problema?',
        'Entrei em contato mais cedo e me disseram que iriam verificar, mas ninguém me respondeu. Vou precisar ficar cobrando toda hora para conseguir uma informação?',
    ],
    [
        'Boa tarde! Recebi minha mercadoria agora e a caixa chegou toda amassada. Quando abri, percebi que o equipamento estava quebrado. Estou muito chateado porque era um produto caro. Como vocês vão resolver isso?',
        'O equipamento custou R$ 3.500,00 e agora não funciona. Tenho a nota fiscal e fotos da embalagem. Preciso saber o que devo fazer para solicitar o ressarcimento.',
        'Sinceramente, estou muito decepcionado. Confiei na empresa para transportar meu equipamento e ele chegou quebrado. Quero falar com alguém responsável por essa situação.',
    ],
    [
        'Bom dia! Preciso enviar uma encomenda para minha mãe, mas nunca utilizei transportadora. Estou um pouco perdido e não sei quais informações preciso apresentar. Você poderia me orientar com calma?',
        'Desculpa, mas não entendi muito bem sua explicação. Você consegue me explicar novamente de uma forma mais simples? Não tenho experiência com esse tipo de envio.',
        'Não tenho muita facilidade com celular e não estou conseguindo enviar os documentos que você pediu. Tem alguma outra forma de fazer isso? Você consegue me orientar?',
    ],
    [
        'Boa tarde! Gostaria de agradecer pelo atendimento que recebi ontem. Fui muito bem atendido, a pessoa teve paciência para explicar tudo e minha mercadoria chegou certinha. Parabéns pelo trabalho de vocês!',
        'Gostei muito do atendimento e pretendo continuar enviando minhas mercadorias com vocês. Inclusive, vou indicar a empresa para alguns amigos. Muito obrigado pela atenção!',
    ],
    [
        'Eu preciso que você me garanta que minha mercadoria vai chegar amanhã, porque tenho um compromisso muito importante. Você consegue me confirmar isso agora?',
        'Estou com pressa e preciso de uma resposta. Você não consegue resolver isso sozinho? Toda vez que pergunto alguma coisa, vocês precisam consultar outra pessoa.',
        'Ontem fui atendido por uma pessoa muito grossa, que parecia não querer trabalhar. Não gostei nada do atendimento. Vocês tratam todos os clientes dessa maneira?',
    ],
    [
        'Muito obrigado pela ajuda! Você foi muito atencioso e conseguiu esclarecer minhas dúvidas. Por enquanto é só isso mesmo.',
        'Certo, então vou aguardar você verificar a situação. Só peço que não esqueça de me dar um retorno, porque realmente preciso resolver isso.',
        'Tudo bem, vou aguardar a solução. Espero que dessa vez consiga resolver, porque já estou bastante desgastado com essa situação. Obrigado.',
    ],
]
QUESTOES = [(grupo, msg) for grupo, mensagens in enumerate(ATENDIMENTOS) for msg in mensagens]
TOTAL = len(QUESTOES)

st.markdown('''<style>
.stApp {background: #f4f7f8;}
.block-container {max-width: 800px; padding-top: 1.5rem;}
.chat-header {background:#075e54; color:white; padding:15px 19px; border-radius:14px 14px 0 0; font-weight:700;}
.chat-bg {background:#e8e2d8; padding:14px 15px 8px; border-radius:0 0 14px 14px; margin-bottom:16px;}
.bubble {padding:10px 14px; border-radius:12px; margin:9px 0; max-width:88%; overflow-wrap:anywhere; white-space:pre-wrap; color:#17242b; box-shadow:0 1px 2px #0001; font-size:0.96rem;}
.client {background:#fff; margin-right:auto; border-top-left-radius:3px;}
.agent {background:#d9fdd3; margin-left:auto; border-top-right-radius:3px;}
.bubble-name {font-size:.73rem; font-weight:700; margin-bottom:4px; color:#14705d;}
.meta {text-align:right; font-size:.67rem; color:#6a777b; margin-top:5px;}
.small-muted {color:#61717a; font-size:.88rem;}
</style>''', unsafe_allow_html=True)


def init():
    defaults = dict(etapa='cadastro', nome='', telefone='', indice=0, respostas=[], inicio=None,
                    inicio_questao=None, fim=None, rascunho='', conversa_id=0)
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def markdown_to_html(texto):
    """Pré-visualização segura das marcações simples do WhatsApp."""
    s = escape(texto)
    s = re.sub(r'\*([^*\n]+)\*', r'<strong>\1</strong>', s)
    s = re.sub(r'_([^_\n]+)_', r'<em>\1</em>', s)
    s = re.sub(r'~([^~\n]+)~', r'<del>\1</del>', s)
    return s.replace('\n', '<br>')


def tempo_fmt(seg):
    seg = max(0, int(seg))
    return f'{seg // 3600:02d}:{(seg % 3600) // 60:02d}:{seg % 60:02d}'


def inserir(s, indice):
    chave = f'rascunho_{indice}'
    st.session_state[chave] = st.session_state.get(chave, '') + s


def font_setup():
    """Fonte Unicode em Windows, Linux ou Streamlit Cloud."""
    candidatos = [
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/arialbd.ttf'),
        ('C:/Windows/Fonts/calibri.ttf', 'C:/Windows/Fonts/calibrib.ttf'),
    ]
    for regular, bold in candidatos:
        if os.path.isfile(regular) and os.path.isfile(bold):
            try:
                pdfmetrics.registerFont(TTFont('FonteApp', regular))
                pdfmetrics.registerFont(TTFont('FonteApp-Bold', bold))
                pdfmetrics.registerFontFamily('FonteApp', normal='FonteApp', bold='FonteApp-Bold')
                return 'FonteApp'
            except Exception:
                continue
    return 'Helvetica'


def pdf_text(s):
    """Sanitiza texto para o ReportLab, preservando acentos e marcações textuais.

    Emojis não são suportados por fontes PDF comuns: sinaliza sua presença.
    """
    saida = []
    em_emoji = False
    for ch in s:
        cp = ord(ch)
        emoji = (0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF)
        if emoji:
            if not em_emoji:
                saida.append(' [emoji] ')
            em_emoji = True
        elif cp in (0xFE0F, 0x200D):
            continue
        else:
            em_emoji = False
            saida.append(ch)
    return escape(''.join(saida)).replace('\n', '<br/>')


def gerar_pdf():
    buf = io.BytesIO()
    fonte = font_setup()
    doc = SimpleDocTemplate(buf, pagesize=(21*cm, 29.7*cm), leftMargin=1.8*cm,
                            rightMargin=1.8*cm, topMargin=1.7*cm, bottomMargin=1.7*cm)
    normal = ParagraphStyle('NormalCustom', fontName=fonte, fontSize=9.2, leading=15, spaceAfter=7)
    titulo = ParagraphStyle('TituloCustom', parent=normal, fontSize=16, leading=22, textColor=colors.HexColor('#075e54'), spaceAfter=14)
    sub = ParagraphStyle('SubCustom', parent=normal, fontSize=11, leading=17, textColor=colors.HexColor('#075e54'), spaceBefore=14, spaceAfter=9)
    cliente = ParagraphStyle('ClienteCustom', parent=normal, leftIndent=0, rightIndent=22, backColor=colors.HexColor('#f1f3f5'), borderPadding=8, spaceBefore=7)
    atendente = ParagraphStyle('AtendenteCustom', parent=normal, leftIndent=22, backColor=colors.HexColor('#e0f5e1'), borderPadding=8, spaceBefore=4)
    miudo = ParagraphStyle('MiudoCustom', parent=normal, fontSize=8, textColor=colors.HexColor('#52656a'))
    story = [Paragraph('Avaliação prática de atendimento', titulo),
             Paragraph(f'<b>Candidato:</b> {pdf_text(st.session_state.nome)}', normal),
             Paragraph(f'<b>Telefone:</b> {pdf_text(st.session_state.telefone)}', normal),
             Paragraph(f'<b>Início:</b> {st.session_state.inicio.strftime("%d/%m/%Y %H:%M:%S")}', normal),
             Paragraph(f'<b>Fim:</b> {st.session_state.fim.strftime("%d/%m/%Y %H:%M:%S")}', normal),
             Paragraph(f'<b>Duração total:</b> {tempo_fmt((st.session_state.fim - st.session_state.inicio).total_seconds())}', normal),
             Paragraph(f'<b>Mensagens respondidas:</b> {len(st.session_state.respostas)}/{TOTAL}', normal),
             HRFlowable(width='100%', color=colors.HexColor('#9ab7af'))]
    for i, ((grupo, pergunta), resposta) in enumerate(zip(QUESTOES, st.session_state.respostas)):
        if i == 0 or grupo != QUESTOES[i-1][0]:
            story.append(Paragraph(f'Atendimento {grupo + 1}', sub))
        story.append(Paragraph(f'<b>Ricardo:</b> {pdf_text(pergunta)}', cliente))
        story.append(Paragraph(f'<b>Candidato:</b> {pdf_text(resposta["texto"])}', atendente))
        story.append(Paragraph(f'Tempo de resposta: {tempo_fmt(resposta["segundos"])} | Enviado em: {resposta["hora"].strftime("%d/%m/%Y %H:%M:%S")}', miudo))
    story.append(Spacer(1, 15))
    story.append(Paragraph('Relatório de simulação de atendimento. Não representa uma conversa real com cliente.', miudo))
    doc.build(story)
    return buf.getvalue()


init()
st.title('💬 Avaliação Prática de Atendimento')
st.caption('Simulação de atendimento • Azul Cargo Express')

if st.session_state.etapa == 'cadastro':
    st.subheader('Identificação do candidato')
    with st.form('cadastro'):
        nome = st.text_input('Nome completo *', max_chars=150)
        telefone = st.text_input('Telefone com DDD *', placeholder='(11) 99999-9999', max_chars=25)
        ok = st.form_submit_button('Continuar', use_container_width=True, type='primary')
    if ok:
        numeros = re.sub(r'\D', '', telefone)
        if len(nome.strip().split()) < 2:
            st.error('Informe seu nome completo.')
        elif len(numeros) not in (10, 11):
            st.error('Informe um telefone válido com DDD (10 ou 11 dígitos).')
        else:
            st.session_state.nome = nome.strip()
            st.session_state.telefone = telefone.strip()
            st.session_state.etapa = 'boas_vindas'
            st.rerun()

elif st.session_state.etapa == 'boas_vindas':
    st.subheader('👋 Seja bem-vindo(a) à nossa Avaliação Prática de Atendimento!')
    st.write('Esta é uma **simulação de atendimento ao cliente via WhatsApp**, desenvolvida para conhecermos melhor sua comunicação escrita, cordialidade, atenção e capacidade de conduzir diferentes situações de atendimento.')
    st.write('Durante a avaliação, você receberá mensagens de um cliente fictício chamado **Ricardo** e deverá respondê-las como se estivesse realizando um atendimento real.')
    st.markdown('''**Orientações importantes:**
- Responda às mensagens de forma educada, clara e profissional.
- Utilize suas próprias palavras, como faria em um atendimento real.
- Você poderá utilizar emojis, negrito e outros recursos de formatação.
- As mensagens aparecerão uma de cada vez, após o envio de cada resposta.
- Todas as mensagens deverão ser respondidas para concluir a avaliação.
- Não é necessário conhecer os procedimentos da empresa. Caso não saiba alguma informação, explique como conduziria a situação.
- Não há limite de caracteres para suas respostas.''')
    st.info('**Importante:** Não estamos avaliando seus conhecimentos técnicos sobre transporte de cargas. Nosso objetivo é conhecer sua forma de se comunicar, escrever e atender clientes.')
    st.write('Ao finalizar, você poderá baixar um PDF com o histórico completo da simulação. **Guarde e entregue esse PDF ao entrevistador**, pois as respostas não são armazenadas em um banco de dados.')
    st.write('**Boa avaliação e sucesso! 💙**')
    if st.button('Iniciar avaliação', type='primary', use_container_width=True):
        st.session_state.inicio = datetime.now()
        st.session_state.inicio_questao = time.monotonic()
        st.session_state.etapa = 'conversa'
        st.rerun()

elif st.session_state.etapa == 'conversa':
    i = st.session_state.indice
    grupo, pergunta = QUESTOES[i]
    st.progress(i / TOTAL, text=f'{i} de {TOTAL} mensagens respondidas')
    if i > 0 and QUESTOES[i-1][0] != grupo:
        st.info('💬 Um novo atendimento está começando. O cliente iniciará outra conversa.')
    st.markdown('<div class="chat-header">🟢 Ricardo — Cliente<br><span style="font-size:12px;font-weight:400">Simulação de WhatsApp</span></div>', unsafe_allow_html=True)
    # Exibe apenas o atendimento atual para evitar misturar conversas independentes.
    historico = []
    for j in range(i):
        if QUESTOES[j][0] == grupo:
            historico.append(('client', 'Ricardo', QUESTOES[j][1]))
            historico.append(('agent', st.session_state.nome.split()[0], st.session_state.respostas[j]['texto']))
    historico.append(('client', 'Ricardo', pergunta))
    bubbles = []
    for tipo, autor, mensagem in historico:
        bubbles.append(f'<div class="bubble {tipo}"><div class="bubble-name">{escape(autor)}</div>{markdown_to_html(mensagem)}</div>')
    st.markdown('<div class="chat-bg">' + ''.join(bubbles) + '</div>', unsafe_allow_html=True)
    st.caption('Digite sua resposta abaixo. Formatação estilo WhatsApp: *negrito*, _itálico_ e ~riscado~.')
    # Barra de emojis simples, acessível também pelo teclado nativo do sistema.
    em = st.columns(8)
    for coluna, emoji in zip(em, ['😊', '🙂', '👍', '🙏', '💙', '✅', '📦', '😉']):
        with coluna:
            st.button(emoji, key=f'emoji_{i}_{emoji}', on_click=inserir, args=(emoji, i), use_container_width=True)
    st.text_area('Sua mensagem *', key=f'rascunho_{i}', height=150, placeholder='Digite aqui como você atenderia o cliente...')
    if st.button('Enviar mensagem ➤', type='primary', use_container_width=True):
        texto = st.session_state.get(f'rascunho_{i}', '')
        if not texto.strip():
            st.warning('Escreva uma resposta antes de enviar.')
        else:
            agora = datetime.now()
            segundos = time.monotonic() - st.session_state.inicio_questao
            st.session_state.respostas.append({'texto': texto.strip(), 'hora': agora, 'segundos': segundos})
            st.session_state.indice += 1
            st.session_state.inicio_questao = time.monotonic()
            if st.session_state.indice == TOTAL:
                st.session_state.fim = agora
                st.session_state.etapa = 'fim'
            st.rerun()

elif st.session_state.etapa == 'fim':
    st.success('🎉 Avaliação concluída! Obrigado pela participação.')
    st.write(f'**Candidato:** {st.session_state.nome}')
    st.write(f'**Mensagens respondidas:** {len(st.session_state.respostas)} de {TOTAL}')
    st.write(f'**Tempo total:** {tempo_fmt((st.session_state.fim-st.session_state.inicio).total_seconds())}')
    try:
        pdf = gerar_pdf()
        slug = re.sub(r'[^a-z0-9]+', '_', st.session_state.nome.lower().encode('ascii', 'ignore').decode()).strip('_')
        st.download_button('📄 Baixar avaliação completa em PDF', data=pdf,
                           file_name=f'avaliacao_atendimento_{slug}_{st.session_state.fim:%Y%m%d_%H%M}.pdf',
                           mime='application/pdf', use_container_width=True, type='primary')
    except Exception as exc:
        st.error(f'Não foi possível gerar o PDF: {exc}')
    st.warning('IMPORTANTE: baixe e entregue o PDF ao entrevistador antes de fechar esta página. O aplicativo não salva respostas em banco de dados. Emojis aparecem identificados como [emoji] no PDF.')
