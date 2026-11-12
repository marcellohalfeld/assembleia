# PLAT-0022: Backup em três camadas — arquivo imutável, cópia dos bancos e dossiês legíveis

- **Status:** Aceita (12/11/2026: "plat-0017 a 0022 aprovadas")
- **Data:** 2026-11-12
- **Decisor:** Marcello
- **Origem:** sessão de 12/11/2026 com o Marcello: "backup como requisito absoluto", com o dado
  cru, o dado processado e relatórios legíveis que recontem a história.

## Contexto

A plataforma vai para produção limitada num servidor doméstico
([PLAT-0020](PLAT-0020-infraestrutura-e-implantacao.md)). Os dados são documentos fiscais,
folhas de pagamento e eventos do eSocial de clientes do escritório, com prazos de guarda e
dados pessoais, inclusive sensíveis ([PLAT-0018](PLAT-0018-dono-de-cada-dado-e-cadastro.md)).
Perder o servidor (disco, roubo, incêndio) não pode significar perder esses dados.

Três tipos de informação precisam sobreviver, e cada um se recupera de um jeito:

- **o dado cru**, o que foi recebido de um órgão público ou enviado a ele (XML de NFS-e e NF-e,
  lotes e retornos do eSocial). É a prova; não se recalcula;
- **o dado processado**, os bancos dos módulos, que podem em parte ser reconstruídos do cru,
  mas com trabalho e com perda das decisões registradas;
- **a história legível**: o que aconteceu, em que ordem, com que resultado, num formato que se
  leia sem a plataforma no ar.

Conferido em 12/11/2026: o aspirador já grava cada XML uma vez, numa pasta por contribuinte,
sem sobrescrever, e guarda o SHA-256 do arquivo no banco (ASP-0005, item 5); a pasta está
organizada pela chave do documento, não pelo hash. A folha grava os eventos baixados e o
registro de envios (JSON Lines) em arquivos soltos, escolhidos na linha de comando, sem hash no
banco.

## Decisão

### 1. Dado cru: arquivo imutável endereçado por SHA-256

1. Todo arquivo recebido de órgão público ou enviado a ele é gravado **uma vez** num arquivo
   imutável, num volume do servidor, endereçado pelo SHA-256 do conteúdo; o banco do módulo
   guarda o hash, com o que identifica o arquivo (tipo, empresa, origem, instante). A gravação é
   atômica e antes da transação do banco; o arquivo nunca é sobrescrito nem apagado pelos
   módulos; a leitura confere o hash.
2. O utilitário de gravação e leitura fica no `blatt-plataforma`
   ([PLAT-0016](PLAT-0016-mapa-de-modulos-e-papeis-dos-repositorios.md)), sem regra de negócio.
3. **Aspirador:** já cumpre o essencial (gravação única, hash no banco); se passa ao endereço por
   hash ou mantém a pasta por chave é decisão `ASP-`, desde que o hash continue no banco.
4. **Folha:** passa a gravar no arquivo imutável os lotes enviados ao eSocial e os retornos
   (recibos, ocorrências, eventos baixados), com o hash no banco. Mudança no `blatt`, em PR lá.

### 2. Dado processado: cópia lógica dos bancos

1. **`pg_dump -Fc` de cada banco toda noite e antes de cada migração**, mais
   **`pg_dumpall --globals-only`** (papéis e *tablespaces*, que o `pg_dump` não inclui). O
   formato *custom* é compactado e restaurado pelo `pg_restore`, inclusive de forma seletiva.
2. A cópia é feita por um papel de backup, só de leitura.
3. **Perda máxima assumida: 24 horas** (o trabalho de um dia). **A confirmar pelo Marcello.**
   Alternativa, se 24 horas for muito: arquivamento contínuo do WAL com cópia base, que permite
   voltar a qualquer instante, ao custo de mais um processo e mais espaço.

### 3. Dossiê legível por empresa e período

1. No fechamento de um período (por exemplo, a competência da folha), o módulo gera um
   **dossiê** da empresa e do período, em **HTML autocontido** (sem dependência externa, legível
   em qualquer navegador) e **CSV**, com:
   - os números do período, como o módulo os apresenta ao usuário;
   - a linha do tempo, tirada da `outbox` e dos registros de execução do módulo;
   - a lista dos arquivos crus do período, com o SHA-256 de cada um.
2. O dossiê é gerado pelo próprio módulo, que é quem entende o conteúdo; o `oper` só o lista no
   portal ([PLAT-0021](PLAT-0021-interface-web.md)). Depois de gerado, é guardado no arquivo
   imutável e entra no backup como os demais.

### 4. Para onde vai: restic, em dois destinos

1. Tudo (arquivo imutável, cópias dos bancos, dossiês) vai para um repositório **restic**,
   **cifrado no servidor antes de sair** (AES-256 em modo CTR com autenticação Poly1305-AES,
   conforme o desenho do restic).
2. **Dois destinos:** um disco local (separado do disco dos dados) e o **Google Drive, via
   rclone** (decidido pelo Marcello). O Drive recebe só dados já cifrados.
3. **A senha do repositório restic fica também com o Marcello, fora do servidor.** O servidor
   precisa dela (como *secret*) para gravar as cópias; sem a cópia fora dele, perder o servidor
   torna o backup ilegível.
4. A política de retenção (quantas cópias diárias, semanais, mensais, anuais) e os prazos
   legais de guarda são **pendência do Marcello**; a retenção é aplicada por
   `restic forget`/`prune` quando decidida. Até lá, nada é apagado.

### 5. Teste de restauração

1. **Mensal**, automático: restaurar a cópia mais recente de cada destino num PostgreSQL
   descartável, rodar `pg_restore` de cada banco, conferir que o executor de migrações reconhece
   todas as migrações aplicadas, conferir por amostragem o hash de arquivos crus restaurados e
   rodar a verificação de integridade do restic (`restic check`, com leitura de uma parte dos
   dados).
2. O resultado (data, destino, o que foi conferido, falhas) aparece no portal; falha é alerta,
   não nota de rodapé.

## Alternativas consideradas

- **Só cópia dos bancos, sem arquivo imutável.** Mais simples, mas o original recebido do
  governo passaria a depender do banco e de quem o grava; o XML é a prova.
- **Cópia física do cluster (`pg_basebackup`) no lugar de `pg_dump`.** Restauração mais
  rápida de tudo de uma vez, mas não por módulo, e só para a mesma versão maior do
  PostgreSQL. Volta a ser opção junto com o arquivamento do WAL (item 2.3).
- **BorgBackup no lugar do restic.** Equivalente em desduplicação e cifragem, mas o destino
  remoto precisa de um Borg do outro lado (por SSH), o que não serve ao Google Drive sem um
  passo a mais (de memória, a conferir); o restic fala com o rclone diretamente.
- **Sincronizar a pasta direto no Google Drive (rclone sync), sem restic.** Dispensa uma
  ferramenta, mas manda dados pessoais sem cifrar ao provedor e não guarda versões.
- **Dossiê só no portal, gerado na hora.** Dispensa arquivo, mas depende da plataforma no ar;
  o objetivo é ler a história sem ela.

## Consequências

- Três lugares para conferir num teste de restauração (arquivo, bancos, dossiês), automatizados
  no serviço de backup do `oper`.
- Espaço: o arquivo imutável só cresce; a desduplicação do restic reduz o custo das cópias
  repetidas dos bancos.
- Dados pessoais e sensíveis saem de casa, cifrados, para o Google Drive. A chave não sai com
  eles.
- A folha ganha trabalho: gravar lotes e retornos no arquivo imutável, com hash no banco, e
  gerar o dossiê da competência (pendência e PR no `blatt`). O aspirador decide o endereço por
  hash numa `ASP-`.
- Até o Marcello decidir retenção e prazos legais, o backup só acumula.

## Referências

- PostgreSQL 16, páginas de manual de `pg_dump` e `pg_dumpall`, lidas no servidor da sessão em
  12/11/2026 (pg_dump 16.15): o formato *custom* (`-Fc`) "suitable for input into pg_restore",
  compactado por padrão; o `pg_dump` não inclui objetos globais (papéis e *tablespaces*), que o
  `pg_dumpall --globals-only` copia. Versão oficial:
  https://www.postgresql.org/docs/current/app-pgdump.html,
  https://www.postgresql.org/docs/current/app-pg-dumpall.html,
  https://www.postgresql.org/docs/current/app-pgrestore.html (o site não abriu na sessão).
- PostgreSQL, arquivamento contínuo e recuperação a um instante:
  https://www.postgresql.org/docs/current/continuous-archiving.html (citado de memória; a
  conferir).
- restic v0.19.1, licença BSD-2-Clause (arquivo `LICENSE`) e documentação no código-fonte,
  lidos em 12/11/2026 pelo proxy de módulos Go: cifragem em `doc/design.rst`; destino via
  rclone (`rclone:<remote>:<path>`) em `doc/030_preparing_a_new_repo.rst`; `forget` com
  `--keep-daily`/`--keep-weekly`/`--keep-monthly` em `doc/060_forget.rst`; `check --read-data`
  em `doc/045_working_with_repos.rst`. Versão publicada:
  https://restic.readthedocs.io/en/stable/ e https://github.com/restic/restic/blob/v0.19.1/LICENSE
  (as páginas não abriram na sessão).
- rclone v1.76.0, licença MIT (arquivo `COPYING`) e documentação do destino Google Drive
  (`docs/content/drive.md`), lidas do código-fonte em 12/11/2026. Versão publicada:
  https://rclone.org/drive/ e https://github.com/rclone/rclone/blob/v1.76.0/COPYING (não
  abriram na sessão).
- ASP-0005, item 5 (pasta de originais como registro de auditoria):
  [aspirador docs/adr/0005](https://github.com/marcellohalfeld/aspirador/blob/claude/admiring-mendel-vilgsf/docs/adr/0005-banco-proprio-fase-1.md).
