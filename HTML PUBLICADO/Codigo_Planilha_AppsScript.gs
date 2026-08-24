/**
 * PROJETO DIGITAL — Backend de sincronização (Google Apps Script)
 * ------------------------------------------------------------------
 * Este código transforma uma Planilha Google em "banco de dados" para o
 * arquivo Projeto_Digital_Ante_Campo.html. Quando alguém marca um poste
 * como feito no site, o código dele entra numa aba da planilha; quando
 * o site consulta o servidor, ele lê essa mesma planilha e mostra pra
 * todo mundo o que já foi feito — exatamente como pedido: "uma lista de
 * excel por trás com o número dos cod_id que estão feitos".
 *
 * COMO USAR: veja o guia COMO_SINCRONIZAR_COM_PLANILHA.md que está na
 * mesma pasta deste arquivo. Resumo: cole este código inteiro em
 * Extensões > Apps Script de uma Planilha Google nova, implante como
 * "Aplicativo da Web" e cole a URL gerada na constante SHEET_API_URL
 * dentro do Projeto_Digital_Ante_Campo.html.
 */

const ABA_POSTES = 'Postes';
const CABECALHO_POSTES = ['cod_id', 'cidade', 'run_id', 'nome', 'cor', 'data_hora'];
const ABA_USUARIOS = 'Usuarios';
const CABECALHO_USUARIOS = ['nome', 'cor'];

function getSheet_(nome, cabecalhos) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(nome);
  if (!sh) {
    sh = ss.insertSheet(nome);
    sh.appendRow(cabecalhos);
  } else if (sh.getLastRow() === 0) {
    sh.appendRow(cabecalhos);
  }
  return sh;
}

function lerLinhas_(sh) {
  const valores = sh.getDataRange().getValues();
  const cabecalhos = valores.shift() || [];
  return valores
    .filter(linha => linha.some(v => String(v).trim() !== ''))
    .map(linha => {
      const obj = {};
      cabecalhos.forEach((c, i) => { obj[c] = linha[i]; });
      return obj;
    });
}

function responderJson_(dados) {
  return ContentService.createTextOutput(JSON.stringify(dados))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  const parametros = (e && e.parameter) || {};
  const cidade = String(parametros.cidade || '');
  const runId = String(parametros.run_id || '');
  const shPostes = getSheet_(ABA_POSTES, CABECALHO_POSTES);
  const shUsuarios = getSheet_(ABA_USUARIOS, CABECALHO_USUARIOS);

  let postes = lerLinhas_(shPostes);
  if (cidade) postes = postes.filter(r => String(r.cidade) === cidade);
  if (runId) postes = postes.filter(r => String(r.run_id) === runId);
  const usuarios = lerLinhas_(shUsuarios);

  return responderJson_({ postes: postes, usuarios: usuarios });
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const corpo = JSON.parse((e.postData && e.postData.contents) || '{}');
    const cidade = String(corpo.cidade || '');
    const runId = String(corpo.run_id || '');
    const shPostes = getSheet_(ABA_POSTES, CABECALHO_POSTES);
    const shUsuarios = getSheet_(ABA_USUARIOS, CABECALHO_USUARIOS);

    if (corpo.usuario && corpo.usuario.nome) {
      upsertUsuario_(shUsuarios, corpo.usuario);
    }

    (corpo.acoes || []).forEach(function (acao) {
      if (acao.tipo === 'marcar') {
        (acao.codIds || []).forEach(function (codId) {
          upsertPoste_(shPostes, {
            cod_id: String(codId),
            cidade: cidade,
            run_id: runId,
            nome: acao.nome,
            cor: acao.cor,
            data_hora: acao.data_hora
          });
        });
      } else if (acao.tipo === 'desmarcar') {
        (acao.codIds || []).forEach(function (codId) {
          removerPoste_(shPostes, String(codId), cidade, runId);
        });
      }
    });

    return doGet({ parameter: { cidade: cidade, run_id: runId } });
  } catch (erro) {
    return responderJson_({ erro: String(erro) });
  } finally {
    lock.releaseLock();
  }
}

function upsertUsuario_(sh, usuario) {
  const dados = sh.getDataRange().getValues();
  const nomeAlvo = String(usuario.nome).trim().toLowerCase();
  for (let i = 1; i < dados.length; i++) {
    if (String(dados[i][0]).trim().toLowerCase() === nomeAlvo) {
      sh.getRange(i + 1, 2).setValue(usuario.cor);
      return;
    }
  }
  sh.appendRow([usuario.nome, usuario.cor]);
}

function upsertPoste_(sh, linha) {
  const dados = sh.getDataRange().getValues();
  for (let i = 1; i < dados.length; i++) {
    if (String(dados[i][0]) === linha.cod_id && String(dados[i][1]) === linha.cidade && String(dados[i][2]) === linha.run_id) {
      sh.getRange(i + 1, 1, 1, 6).setValues([[linha.cod_id, linha.cidade, linha.run_id, linha.nome, linha.cor, linha.data_hora]]);
      return;
    }
  }
  sh.appendRow([linha.cod_id, linha.cidade, linha.run_id, linha.nome, linha.cor, linha.data_hora]);
}

function removerPoste_(sh, codId, cidade, runId) {
  const dados = sh.getDataRange().getValues();
  for (let i = dados.length - 1; i >= 1; i--) {
    if (String(dados[i][0]) === codId && String(dados[i][1]) === cidade && String(dados[i][2]) === runId) {
      sh.deleteRow(i + 1);
    }
  }
}
