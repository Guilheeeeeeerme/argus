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
  'Empresa ativa': 'Active company',
  'Estabelecimento': 'Establishment',
  'Estabelecimento ativo': 'Active establishment',
  'Nenhum estabelecimento selecionado': 'No establishment selected',
  'Empresa atualizada.': 'Company context updated.',
  'Estabelecimento ativo: {name}': 'Active establishment: {name}',
  'Estabelecimento removido.': 'Establishment cleared.',
  'Excluir {name}?': 'Delete {name}?',
  'Excluir {name}? Essa ação não pode ser desfeita.': 'Delete {name}? This cannot be undone.',
  'Cancelar': 'Cancel',
  'Salvar': 'Save',
  'Fechar': 'Close',
  'Carregando': 'Loading',
  'Carregando casos': 'Loading cases',
  'Excluir empresa': 'Delete company',
  'Editar empresa': 'Edit company',
  'Excluir usuário': 'Delete user',
  'Excluir estabelecimento': 'Delete establishment',
  'Editar estabelecimento': 'Edit establishment',
  'Contexto de empresa': 'Tenant context',
  'Nenhuma empresa ainda': 'No companies yet',
  'Crie a primeira empresa para começar.': 'Create a company to start multi-tenant administration.',
  'Nenhum usuário ainda': 'No users yet',
  'Crie um gestor ou operador para esta empresa.': 'Create a manager or operator for the active company.',
  'Nenhum estabelecimento ainda': 'No establishments yet',
  'Adicione um estabelecimento para gerenciar câmeras e instruções.': 'Add an establishment, then manage its cameras and prompts.',
  'Nenhum caso ainda': 'No cases yet',
  'Novas detecções aparecerão aqui em tempo real.': 'New detections will appear here in real time.',
  'Selecione um caso': 'Select a case',
  'Escolha um item da lista para revisar e resolver.': 'Choose an item from the feed to review evidence and resolve.',
  'Ao vivo': 'Live',
  'Desconectado': 'Disconnected',
  'Conectando…': 'Connecting…',
  'Empresas': 'Companies',
  'Usuários': 'Users',
  'Estabelecimentos': 'Establishments',
  'Câmeras': 'Cameras',
  'Instruções': 'Prompts',
  'Conjunto de instruções': 'Prompt set',
  'Webhooks': 'Webhooks',
  'Editar': 'Edit',
  'Excluir': 'Delete',
  'Nova empresa': 'New company',
  'Empresa criada.': 'Company created.',
  'Nome da empresa': 'Company name',
  'Criar empresa': 'Create company',
  'Usuário criado.': 'User created.',
  'E-mail do usuário': 'User email',
  'E-mail': 'Email',
  'Senha': 'Password',
  'Função do usuário': 'User role',
  'Gestor': 'Manager',
  'Operador': 'Operator',
  'Criar usuário': 'Create user',
  'Novo estabelecimento': 'New establishment',
  'Nova câmera': 'New camera',
  'Estabelecimento criado.': 'Establishment created.',
  'Nome do estabelecimento': 'Establishment name',
  'Endereço': 'Address',
  'sem endereço': 'no address',
  'Criar estabelecimento': 'Create establishment',
  'Nome da câmera': 'Camera name',
  'URL do stream (RTSP)': 'Stream URL (RTSP)',
  'Adicionar câmera': 'Add camera',
  'Nenhuma câmera ainda': 'No cameras yet',
  'Adicione uma câmera com a URL RTSP do stream.': 'Add a camera with an RTSP stream URL.',
  'Câmeras · {name}': 'Cameras · {name}',
  'Fechar câmeras': 'Close cameras',
  'Nenhuma instrução ainda': 'No prompts yet',
  'Adicione instruções que definem detecções positivas.': 'Add prompts that define positive detections.',
  'Texto da instrução': 'Prompt body',
  'Adicionar instrução': 'Add prompt',
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
  'Criar webhook': 'Create webhook',
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
  'Trocar de empresa': 'Change company',
  'Selecione uma empresa ou peça acesso a um administrador.': 'Select a company or ask an administrator for access.',
  'Nenhuma empresa selecionada': 'No company selected',
  'Selecione uma empresa': 'Select a company',
  'Escolha uma empresa na barra lateral para continuar.': 'Choose a company in the sidebar to continue.',
  'Fale com um administrador para ter acesso.': 'Contact an administrator to get access to a company.',
  'Acesso à empresa atualizado.': 'Company access updated.',
  'Dar acesso a {name}': 'Add access to {name}',
  'Remover acesso a {name}': 'Remove access to {name}',
  'Nenhuma empresa atribuída ainda.': 'No company assigned yet.',
  'Peça acesso a um administrador.': 'Ask an administrator for access.',
  'Triagem': 'Triage',
  'Triagem conectada.': 'Live triage connected.',
  'Falha na conexão com o WebSocket.': 'WebSocket connection failed.',
  'Conexão perdida. Atualize a página para reconectar.': 'WebSocket disconnected; refresh to reconnect.',
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

export function localizeApiError(message: string, t: TFunction): string {
  const normalized = message.toLowerCase();
  if (normalized.includes('already registered'))
    return t('Este e-mail já está cadastrado.');
  if (normalized.includes('invalid email or password'))
    return t('E-mail ou senha inválidos.');
  if (normalized.includes('at least 8'))
    return t('A senha deve ter pelo menos 8 caracteres.');
  return t('Ocorreu um erro. Tente novamente.');
}
