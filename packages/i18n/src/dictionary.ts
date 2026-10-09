export const SUPPORTED_LOCALES = ['pt-BR', 'en'] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];
export type TranslationKey = string;
export type TranslationVars = Record<string, string | number>;
export type TFunction = (key: string, vars?: TranslationVars) => string;

function isLocale(value: string): value is Locale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value);
}

/**
 * pt-BR is the product's primary language. English is opted into explicitly;
 * anything else falls back to pt-BR.
 */
export function resolveLocale(candidate: string | null | undefined): Locale {
  if (candidate && isLocale(candidate)) return candidate;
  if (candidate?.startsWith('en')) return 'en';
  return 'pt-BR';
}

// pt-BR is canonical: keys are the Portuguese copy and render as-is.
// `en` maps Portuguese keys to English; missing entries fall back to pt-BR.
const en: Record<string, string> = {
  'Entrar': 'Sign in',
  'Entre para continuar.': 'Sign in to continue.',
  'Sair': 'Log out',
  'Sair?': 'Log out?',
  'Encerrar a sessão neste dispositivo?': 'End your session on this device?',
  'Idioma': 'Language',
  'English': 'English',
  'Administração': 'Administration',
  'Abrir Triagem': 'Open Triage',
  'Empresa': 'Company',
  'Excluir {name}? Essa ação não pode ser desfeita.': 'Delete {name}? This cannot be undone.',
  'Cancelar': 'Cancel',
  'Salvar': 'Save',
  'Fechar': 'Close',
  'Carregando': 'Loading',
  'Carregando casos': 'Loading cases',
  'Excluir usuário': 'Delete user',
  'Nenhum usuário ainda': 'No users yet',
  'Nenhum caso ainda': 'No cases yet',
  'Novas detecções aparecerão aqui em tempo real.': 'New detections will appear here in real time.',
  'Ao vivo': 'Live',
  'Desconectado': 'Disconnected',
  'Conectando…': 'Connecting…',
  'Usuários': 'Users',
  'Câmeras': 'Cameras',
  'Instruções': 'Prompts',
  'Conjunto de instruções': 'Prompt set',
  'Webhooks': 'Webhooks',
  'Editar': 'Edit',
  'Excluir': 'Delete',
  'Usuário criado.': 'User created.',
  'E-mail do usuário': 'User email',
  'E-mail': 'Email',
  'Senha': 'Password',
  'Gestor': 'Manager',
  'Operador': 'Operator',
  'Nova câmera': 'New camera',
  'Endereço': 'Address',
  'sem endereço': 'no address',
  'Nome da câmera': 'Camera name',
  'URL do stream (RTSP)': 'Stream URL (RTSP)',
  'Nenhuma câmera ainda': 'No cameras yet',
  'Adicione uma câmera com a URL RTSP do stream.': 'Add a camera with an RTSP stream URL.',
  'Nenhuma instrução ainda': 'No prompts yet',
  'Adicione instruções que definem detecções positivas.': 'Add prompts that define positive detections.',
  'Texto da instrução': 'Prompt body',
  'Editar instrução': 'Edit prompt',
  'Ativa': 'Enabled',
  'Inativa': 'Disabled',
  'Ativar': 'Enable',
  'Desativar': 'Disable',
  'Instrução salva.': 'Prompt saved.',
  'Instrução criada.': 'Prompt created.',
  'Nenhum webhook ainda': 'No webhook endpoints yet',
  'Crie um webhook para receber eventos externos.': 'Create an endpoint to receive external context events.',
  'Nome do webhook': 'Webhook name',
  'Webhook criado. Copie o token agora — ele não será exibido novamente.': 'Webhook created. Copy the token now — it will not be shown again.',
  'Token (copie agora)': 'Token (copy now)',
  'Este e-mail já está cadastrado.': 'This email is already registered.',
  'E-mail ou senha inválidos.': 'Invalid email or password.',
  'A senha deve ter pelo menos 8 caracteres.': 'Password must be at least 8 characters.',
  'Ocorreu um erro. Tente novamente.': 'An error occurred. Please try again.',
  'Mudar idioma': 'Switch language',
  'Mudar para modo claro': 'Switch to light mode',
  'Mudar para modo escuro': 'Switch to dark mode',
  'Verificando sessão…': 'Checking session…',
  'Redirecionando para o login…': 'Redirecting to sign in…',
  'Fale com um administrador para ter acesso.': 'Contact an administrator to get access to an account.',
  'Triagem': 'Triage',
  'Fila de casos': 'Case feed',
  '{confidence}% de confiança': '{confidence}% confidence',
  'Caso atualizado.': 'Case updated.',
  'Detalhes do caso': 'Case detail',
  'Resumo': 'Summary',
  'Instruções acionadas': 'Prompt hits',
  'Evidência': 'Evidence',
  'Carregando clipe de evidência…': 'Loading evidence clip…',
  'Não foi possível carregar o clipe.': 'Unable to load evidence clip.',
  'Sem clipe ou frames de evidência.': 'No evidence clip or frames.',
  'Justificativa (opcional; recomendada para falso positivo)': 'Reasoning (optional, recommended for false positive)',
  'Justificativa obrigatória para falso positivo.': 'Reasoning is required for false positive.',
  'Confirmar': 'Confirm',
  'Descartar': 'Dismiss',
  'Falso positivo': 'False positive',
  'Selecione…': 'Select…',
  'Aberto': 'Open',
  'Confirmado': 'Confirmed',
  'Descartado': 'Dismissed',
  'Root': 'Root',
  'Administrador': 'Administrator',

  // ——— Admin UX (Conta / Unidade vocabulary) ———
  'Conta': 'Account',
  'Contas': 'Accounts',
  'Conta ativa': 'Active account',
  'Contexto da conta': 'Account context',
  'Nenhuma conta selecionada': 'No account selected',
  'Selecione uma conta': 'Select an account',
  'A triagem exige uma conta ativa. Selecione uma conta na administração ou peça acesso a um administrador.':
    'Triage requires an active account. Select an account in admin or ask an administrator for access.',
  'Sessão inválida ou API indisponível. Entre novamente ou selecione uma conta.':
    'Invalid session or API unavailable. Sign in again or select an account.',
  'Escolha uma conta na barra lateral para continuar.': 'Choose an account in the sidebar to continue.',
  'Nenhuma conta atribuída ainda.': 'No account assigned yet.',
  'Nenhuma conta ainda': 'No accounts yet',
  'Crie a primeira conta para começar.': 'Create the first account to get started.',
  'Nova conta': 'New account',
  'Editar conta': 'Edit account',
  'Excluir conta': 'Delete account',
  'Nome da conta': 'Account name',
  'Identificador (slug)': 'Identifier (slug)',
  'Usado em URLs e integrações. Letras minúsculas, números e hífens.': 'Used in URLs and integrations. Lowercase letters, numbers and hyphens.',
  'Conta criada.': 'Account created.',
  'Conta salva.': 'Account saved.',
  'Conta excluída.': 'Account deleted.',
  'Conta atualizada.': 'Account context updated.',
  'Trocar de conta': 'Switch account',
  'Acesso à conta atualizado.': 'Account access updated.',
  'Acesso às contas': 'Account access',
  'Gestores e operadores só veem as contas marcadas.': 'Managers and operators only see the selected accounts.',
  'Gestores e operadores das contas, além dos administradores da plataforma.': 'Account managers and operators, plus platform administrators.',
  'Você está editando o seu próprio usuário.': 'You are editing your own user.',
  'Empresa, ONG, escola ou universidade que usa o Argus.': 'Company, NGO, school or university using Argus.',
  'Empresas, ONGs, escolas e universidades atendidas por esta plataforma.': 'Companies, NGOs, schools and universities served by this platform.',
  'Use apenas letras minúsculas, números e hífens.': 'Use lowercase letters, numbers and hyphens only.',
  'Usar esta conta': 'Use this account',
  'Plataforma': 'Platform',
  'Resumo de {name}.': 'Summary for {name}.',
  'Unidade': 'Unit',
  'Unidades': 'Units',
  'Unidade ativa': 'Active unit',
  'Nenhuma unidade selecionada': 'No unit selected',
  'Todas as unidades': 'All units',
  'Nenhuma unidade ainda': 'No units yet',
  'Adicione uma unidade para gerenciar câmeras e instruções.': 'Add a unit to manage its cameras and prompts.',
  'Nova unidade': 'New unit',
  'Lojas, salas ou campi desta conta. Cada unidade agrupa câmeras, instruções e webhooks.': 'Stores, rooms or campuses of this account. Each unit groups cameras, prompts and webhooks.',
  'Editar unidade': 'Edit unit',
  'Excluir unidade': 'Delete unit',
  'Nome da unidade': 'Unit name',
  'Fuso horário': 'Time zone',
  'Unidade criada.': 'Unit created.',
  'Unidade salva.': 'Unit saved.',
  'Unidade excluída.': 'Unit deleted.',
  'Unidade ativa: {name}': 'Active unit: {name}',
  'Unidade removida.': 'Unit cleared.',
  'Unidade não encontrada.': 'Unit not found.',
  'Editar câmera': 'Edit camera',
  'Excluir câmera': 'Delete camera',
  'Câmera criada.': 'Camera created.',
  'Câmera salva.': 'Camera saved.',
  'Câmera excluída.': 'Camera deleted.',
  'Câmera ativa': 'Camera enabled',
  'Câmera ativada.': 'Camera enabled.',
  'Câmera desativada.': 'Camera disabled.',
  'Mostrar inativas': 'Show inactive',
  'Usuário do stream': 'Stream username',
  'Senha do stream': 'Stream password',
  'Deixe em branco para manter a senha atual.': 'Leave blank to keep the current password.',
  'Nova instrução': 'New prompt',
  'Excluir instrução': 'Delete prompt',
  'Instrução excluída.': 'Prompt deleted.',
  'Instrução ativada.': 'Prompt enabled.',
  'Instrução desativada.': 'Prompt disabled.',
  'Nome do conjunto': 'Set name',
  'Conjunto': 'Set',
  'Câmera': 'Camera',
  'Seções da unidade': 'Unit sections',
  'Descreva em linguagem natural o que deve gerar uma detecção positiva.': 'Describe in natural language what should trigger a positive detection.',
  'Webhooks desta unidade recebem eventos externos de contexto.': 'Webhooks of this unit receive external context events.',
  'Novo conjunto de instruções': 'New prompt set',
  'Renomear conjunto': 'Rename set',
  'Excluir conjunto': 'Delete set',
  'Conjunto criado.': 'Prompt set created.',
  'Conjunto salvo.': 'Prompt set saved.',
  'Conjunto excluído.': 'Prompt set deleted.',
  'Selecione uma câmera': 'Select a camera',
  'Escolha uma câmera para ver suas instruções.': 'Choose a camera to see its prompts.',
  'Nenhum conjunto de instruções ainda': 'No prompt set yet',
  'Crie um conjunto para começar a adicionar instruções.': 'Create a set to start adding prompts.',
  'Novo webhook': 'New webhook',
  'Editar webhook': 'Edit webhook',
  'Excluir webhook': 'Delete webhook',
  'Webhook salvo.': 'Webhook saved.',
  'Webhook excluído.': 'Webhook deleted.',
  'Webhook ativo': 'Webhook enabled',
  'Rotacionar token': 'Rotate token',
  'Rotacionar token?': 'Rotate token?',
  'O token atual deixa de funcionar imediatamente.': 'The current token stops working immediately.',
  'Token rotacionado. Copie o novo token agora.': 'Token rotated. Copy the new token now.',
  'Copiar': 'Copy',
  'Copiado': 'Copied',
  'Token copiado.': 'Token copied.',
  'Novo usuário': 'New user',
  'Editar usuário': 'Edit user',
  'Usuário salvo.': 'User saved.',
  'Usuário excluído.': 'User deleted.',
  'Nova senha (opcional)': 'New password (optional)',
  'Função': 'Role',
  'Nenhum acesso': 'No access',
  'Crie um gestor ou operador e dê acesso às contas.': 'Create a manager or operator and grant account access.',
  'Visão geral': 'Overview',
  'Notificações': 'Notifications',
  'Navegação estrutural': 'Breadcrumb',
  'Página não encontrada': 'Page not found',
  'Sem permissão': 'No permission',
  'Você não tem permissão para ver esta página.': 'You do not have permission to view this page.',
  'Voltar': 'Back',
  'Ver todas': 'View all',
  'Ver todos': 'View all',
  'Nome': 'Name',
  'Criar': 'Create',
  'Salvando…': 'Saving…',
  'Excluindo…': 'Deleting…',
  'Trocando…': 'Switching…',
  'Carregando…': 'Loading…',
  'Tentar novamente': 'Try again',
  'Campo obrigatório': 'Required field',
  'Não foi possível carregar.': 'Could not load.',
  'Nenhum resultado': 'No results',
  'Ativo': 'Enabled',
  'Inativo': 'Disabled',
  'Mostrar': 'Show',
  'Ocultar': 'Hide',
  'Conta não encontrada.': 'Account not found.',
  'Sem acesso a esta conta.': 'No access to this account.',
  'Você não tem permissão para esta ação.': 'You do not have permission for this action.',
  'Câmera não encontrada.': 'Camera not found.',
  'Conjunto de instruções não encontrado.': 'Prompt set not found.',
  'Instrução não encontrada.': 'Prompt not found.',
  'Webhook não encontrado.': 'Webhook not found.',
  'Usuário não encontrado.': 'User not found.',
  'Função inválida.': 'Invalid role.',
  'Este caso já foi resolvido.': 'This case has already been resolved.',
  'Selecione uma conta primeiro.': 'Select an account first.',
  'Sua sessão expirou. Entre novamente.': 'Your session expired. Sign in again.',
  'Serviço indisponível. Tente novamente em instantes.': 'Service unavailable. Try again shortly.',
  'Sem conexão com o servidor.': 'Cannot reach the server.',
  'Já existe um registro com esse valor.': 'A record with this value already exists.',
  'Dados inválidos. Revise os campos.': 'Invalid data. Review the fields.',
  'Versão desatualizada. Recarregue a página.': 'Outdated version. Reload the page.',
  'Tipo de conta': 'Account type',
  'ONG': 'NGO',
  'Escola': 'School',
  'Universidade': 'University',
  'Outro': 'Other',

  // ——— Triage grid ———
  'Selecione uma conta ou peça acesso a um administrador.': 'Select an account or ask an administrator for access.',
  'Selecione uma unidade': 'Select a unit',
  'Escolha a unidade cujas câmeras você vai acompanhar.': 'Choose the unit whose cameras you will monitor.',
  'Nenhuma unidade cadastrada nesta conta. Crie uma na administração.': 'No unit registered in this account. Create one in Administration.',
  'Nenhuma câmera nesta unidade': 'No cameras in this unit',
  'Cadastre câmeras na administração para vê-las aqui.': 'Register cameras in Administration to see them here.',
  'Sem sinal': 'No signal',
  'Reconectando…': 'Reconnecting…',
  'Caso': 'Case',
  'Sem casos para esta câmera.': 'No cases for this camera.',
  '{count} casos abertos': '{count} open cases',
  '{count} novos': '{count} new',
};

const dictionaries: Record<Locale, Record<string, string>> = {
  'pt-BR': {},
  en,
};

export function translate(locale: Locale, key: string, vars?: TranslationVars): string {
  let value = locale === 'pt-BR' ? key : (dictionaries[locale][key] ?? key);
  if (vars) {
    value = value.replace(/\{(\w+)\}/g, (match, name: string) =>
      name in vars ? String(vars[name]) : match,
    );
  }
  return value;
}

/** Triage case states arrive as raw API enums; map them to localized labels. */
const TRIAGE_STATE_LABELS: Record<string, string> = {
  open: 'Aberto',
  confirmed: 'Confirmado',
  dismissed: 'Descartado',
  false_positive: 'Falso positivo',
};

export function triageStateLabel(state: string, t: TFunction): string {
  const key = TRIAGE_STATE_LABELS[state];
  return key ? t(key) : state;
}

/** User roles arrive as raw API enums; map them to localized labels. */
const ROLE_LABELS: Record<string, string> = {
  manager: 'Gestor',
  operator: 'Operador',
  root: 'Root',
  admin: 'Administrador',
};

export function roleLabel(role: string, t: TFunction): string {
  const key = ROLE_LABELS[role];
  return key ? t(key) : role;
}

/** Ordered (needle, pt-BR key) pairs matched against the lower-cased API detail. */
const API_ERROR_PATTERNS: ReadonlyArray<readonly [string, string]> = [
  ['already registered', 'Este e-mail já está cadastrado.'],
  ['invalid email or password', 'E-mail ou senha inválidos.'],
  ['at least 8', 'A senha deve ter pelo menos 8 caracteres.'],
  ['unit not found', 'Unidade não encontrada.'],
  ['establishment not found', 'Unidade não encontrada.'],
  ['account not found', 'Conta não encontrada.'],
  ['company not found', 'Conta não encontrada.'],
  ['client not found', 'Conta não encontrada.'],
  ['account access denied', 'Sem acesso a esta conta.'],
  ['company access denied', 'Sem acesso a esta conta.'],
  ['renamed: use /v1/accounts', 'Versão desatualizada. Recarregue a página.'],
  ['insufficient permissions', 'Você não tem permissão para esta ação.'],
  ['platform role required', 'Você não tem permissão para esta ação.'],
  ['camera not found', 'Câmera não encontrada.'],
  ['promptset not found', 'Conjunto de instruções não encontrado.'],
  ['prompt not found', 'Instrução não encontrada.'],
  ['webhook endpoint not found', 'Webhook não encontrado.'],
  ['user not found', 'Usuário não encontrado.'],
  ['invalid user role', 'Função inválida.'],
  ['triage case already resolved', 'Este caso já foi resolvido.'],
  ['select an account first', 'Selecione uma conta primeiro.'],
  ['select a company first', 'Selecione uma conta primeiro.'],
  ['session expired', 'Sua sessão expirou. Entre novamente.'],
  ['token expired', 'Sua sessão expirou. Entre novamente.'],
  ['invalid token', 'Sua sessão expirou. Entre novamente.'],
  ['missing bearer token', 'Sua sessão expirou. Entre novamente.'],
  ['database unavailable', 'Serviço indisponível. Tente novamente em instantes.'],
  ['storage unavailable', 'Serviço indisponível. Tente novamente em instantes.'],
  ['failed to fetch', 'Sem conexão com o servidor.'],
  ['networkerror', 'Sem conexão com o servidor.'],
  ['load failed', 'Sem conexão com o servidor.'],
  ['network error', 'Sem conexão com o servidor.'],
  ['duplicate key', 'Já existe um registro com esse valor.'],
  ['already exists', 'Já existe um registro com esse valor.'],
  ['unique constraint', 'Já existe um registro com esse valor.'],
  ['validation error', 'Dados inválidos. Revise os campos.'],
  ['field required', 'Campo obrigatório'],
];

function errorDetail(error: unknown): string {
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object') {
    const detail = (error as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
    const message = (error as { message?: unknown }).message;
    if (typeof message === 'string') return message;
  }
  return String(error ?? '');
}

/**
 * Map an API failure (`ApiError`, `Error` or raw detail string) to localized copy.
 * Unknown details fall back to a generic retry message.
 */
export function localizeApiError(error: unknown, t: TFunction): string {
  const normalized = errorDetail(error).toLowerCase();
  for (const [needle, key] of API_ERROR_PATTERNS) {
    if (normalized.includes(needle)) return t(key);
  }
  return t('Ocorreu um erro. Tente novamente.');
}
