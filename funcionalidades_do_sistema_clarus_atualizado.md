# FUNCIONALIDADES DO SISTEMA – CLARUS

Este documento consolida as funcionalidades atuais **e as funcionalidades em processo**, incorporando módulos estratégicos de SST, auditoria, mobilidade e inteligência artificial.

---

## 1) Multi-tenant e configurações

- Gestão de empresas (tenants) com isolamento por schema.
- Domínios e subdomínios por empresa.
- Ativação/desativação de módulos por empresa.
- Parâmetros globais e específicos por tenant.

---

## 2) Usuários, perfis e permissões

- Usuários vinculados a funcionários, setores e plantas.
- Perfis e grupos de permissões por módulo e ação.
- Controle de acesso administrativo e operacional.
- Registro de acessos e tentativas.

---

## 3) Cadastros base

- Cargos e setores.
- Depósitos com regra de bloqueio de saldo negativo.
- Fornecedores.
- Tipos de funcionário com regras de produtos permitidos.
- Plantas, centros de custo, turnos e GHE.
- Motivos de afastamento.
- Riscos ocupacionais com nível e descrição.

---

## 4) Produtos e EPI

- Cadastro completo de produtos (EPI/EPC): foto, códigos, referência, periodicidade, impostos, marca e unidade.
- Classificação por tipo, família, subfamília e localização.
- Regras de controle:
  - Monitoramento de uso.
  - Troca periódica por funcionário.
  - Obrigatoriedade de entrega.
- Estoque mínimo e ideal.
- Produto ativo/inativo.
- Fornecedores por produto com CA, códigos, preço e fator de compra.
- Anexos por produto com limite de tamanho.
- Histórico completo de movimentações e logs.
- Integração com base oficial de CA EPI (consulta por CA, descrição, fornecedor e validade).

---

## 5) Estoque

- Saldo por produto, grade, depósito e planta.
- Movimentações de entrada, saída e transferência.
- Bloqueio de saldo negativo conforme configuração do depósito.
- Extrato de produto/recurso com filtros (data, tipo, depósito, produto e grade).
- Logs detalhados de todas as ações.

---

## 6) Entregas de EPI

- Criação de entregas e solicitações.
- Itens por funcionário com validação por tipo de funcionário.
- Validação de recebimento:
  - Senha
  - Assinatura digital
  - Confirmação via celular
- Baixa automática no estoque.
- Histórico de entregas no prontuário do funcionário.
- Atendimento, detalhamento e cancelamento de entregas.

---

## 7) Funcionários (RH)

- Cadastro completo de funcionários.
- Vínculo com cargo, setor, planta, centro de custo, GHE e turno.
- Definição de líder e gestor.
- Controle de admissão e demissão.
- Afastamentos, advertências e históricos.
- Anexos de documentos.
- Associação de riscos ocupacionais.
- Definição de EPIs permitidos e obrigatórios.

---

## 8) Acessos e terceiros

- Cadastro de empresas parceiras e terceiros.
- Controle de acesso com verificação de EPI e treinamentos.
- Gestão de consumo de EPI por parceiros.
- Separação de estoque para visitantes e empréstimos.
- Controle de devolução de EPIs emprestados.

---

## 9) Treinamentos

- Cadastro de treinamentos (tipo, validade e obrigatoriedade).
- Turmas, agenda e instrutores.
- Controle de presença e avaliação.
- Emissão de certificados.
- Controle de vencimentos e pendências.
- Alertas automáticos de revalidação.

---

## 10) Relatórios e dashboards

- Editor de relatórios configurável.
- Dashboards com indicadores de SST.
- Filtros por período, planta, setor e empresa.
- Séries temporais (dia, semana, mês).
- Exportação para PDF e Excel.

---

## 11) Módulo de Auditoria **(EM PROCESSO)**

- Registro completo de ações do sistema (quem, quando, o quê).
- Auditoria de:
  - Entregas e cancelamentos de EPI.
  - Alterações de estoque.
  - Alterações em cadastros sensíveis.
- Linha do tempo por funcionário, produto ou empresa.
- Evidências para auditorias internas e externas.
- Relatórios de conformidade.

---

## 12) Inteligência Artificial – **Clara (IA do Clarus)** **(EM PROCESSO)**

A **Clara** é a assistente inteligente do sistema Clarus.

### Funções da Clara:

- Analisar consumo de EPI e sugerir compras.
- Identificar EPIs vencidos ou próximos do vencimento.
- Alertar sobre funcionários fora de conformidade.
- Sugerir ajustes de estoque mínimo/ideal.
- Auxiliar auditorias com respostas automáticas.
- Apoiar usuários com perguntas em linguagem natural.
- Gerar insights de risco e não conformidade.

---

## 13) Carteira Digital do Colaborador (QR Code) **(EM PROCESSO)**

- Carteira digital acessível pelo celular.
- QR Code individual do colaborador.
- Consulta rápida de:
  - EPIs entregues e válidos.
  - Treinamentos realizados e pendentes.
  - Situação de conformidade.
- Ideal para portarias, obras e auditorias em campo.

---

## 14) Solicitação de EPI via celular **(EM PROCESSO)**

- Portal/mobile para colaboradores.
- Solicitação rápida de EPIs.
- Validação automática de elegibilidade.
- Aprovação por gestor (quando configurado).
- Integração direta com estoque e entregas.

---

## 15) Necessidade de compra (Compras) **(EM PROCESSO)**

- Geração automática de necessidades de compra.
- Baseado em:
  - Estoque mínimo/ideal.
  - Consumo histórico.
  - Troca periódica de EPIs.
- Relatórios para o setor de compras.

---

## 16) Conformidade legal e auditorias **(EM PROCESSO)**

- Aderência às Normas Regulamentadoras (NRs).
- Atualizações contínuas conforme legislação vigente.
- Base preparada para fiscalizações e auditorias.

---

## 17) Integração com eSocial **(EM PROCESSO)**

- Consolidação de dados exigidos pelo eSocial.
- Informações de:
  - Funcionários
  - EPIs entregues
  - Treinamentos
  - Riscos
- Exportação e integração com sistemas externos.

---

## 18) Alertas e notificações **(EM PROCESSO)**

- Alertas de:
  - Troca periódica de EPI.
  - Vencimento de CA.
  - Vencimento de treinamentos.
- Notificações por sistema, e-mail ou push.

---

## 19) Módulos SST  **(EM PROCESSO)**

### 19.1 Módulo de CIPA

- Gestão de eleições.
- Cadastro e histórico de cipeiros.
- Mandatos e atas.

### 19.2 Módulo de Acidente de Trabalho

- Registro de acidentes e incidentes.
- Classificação e análise.
- Histórico por funcionário.

### 19.3 Controle de Desvios

- Registro de desvios de segurança.
- Ações corretivas e preventivas.
- Acompanhamento de status.

### 19.4 Inspeções (Checklists)

- Checklists configuráveis.
- Inspeções via celular.
- Registro de evidências.

### 19.5 Módulo de Saúde (PCMSO)

- Controle de exames ocupacionais.
- Atestados médicos.
- Configuração de exames por função.

### 19.6 Módulo PGR

- Cadastro de perigos e riscos.
- Avaliação e plano de ação.
- Integração com EPIs e treinamentos.

---



