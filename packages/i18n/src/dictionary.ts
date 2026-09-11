export const SUPPORTED_LOCALES = ['en', 'pt-BR'] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];
export type TranslationKey = string;
export type TranslationVars = Record<string, string | number>;
export type TFunction = (key: string, vars?: TranslationVars) => string;

function isLocale(value: string): value is Locale {
  return (SUPPORTED_LOCALES as readonly string[]).includes(value);
}

export function resolveLocale(candidate: string | null | undefined): Locale {
  if (candidate && isLocale(candidate)) return candidate;
  if (candidate?.startsWith('pt')) return 'pt-BR';
  return 'en';
}

const ptBR: Record<string, string> = {
  'Sign in': 'Entrar',
  'Sign in to continue.': 'Entre para continuar.',
  'Sign out': 'Sair',
  'Log out': 'Sair',
  'Log out?': 'Sair?',
  'Language': 'Idioma',
  'English': 'English',
  'Português (Brasil)': 'Português (Brasil)',
  'Administration': 'Administração',
  'Open Triage': 'Abrir Triagem',
  'Company': 'Empresa',
  'Active company': 'Empresa ativa',
  'All companies': 'Todas as empresas',
  'Establishment': 'Estabelecimento',
  'Active establishment': 'Estabelecimento ativo',
  'No establishment selected': 'Nenhum estabelecimento selecionado',
  'Company context updated.': 'Contexto de empresa atualizado.',
  'Active establishment: {name}': 'Estabelecimento ativo: {name}',
  'Establishment cleared.': 'Estabelecimento removido.',
  'Signed in as {email} ({role})': 'Conectado como {email} ({role})',
  'Delete {name}?': 'Excluir {name}?',
  'Delete {name}? This cannot be undone.': 'Excluir {name}? Esta ação não pode ser desfeita.',
  'Cancel': 'Cancelar',
  'Save': 'Salvar',
  'Close': 'Fechar',
  'Loading': 'Carregando',
  'Loading cases': 'Carregando casos',
  'Delete company': 'Excluir empresa',
  'Edit company': 'Editar empresa',
  'Delete user': 'Excluir usuário',
  'Delete establishment': 'Excluir estabelecimento',
  'Edit establishment': 'Editar estabelecimento',
  'End your session on this device?': 'Encerrar sua sessão neste dispositivo?',
  'Tenant context': 'Contexto do locatário',
  'No companies yet': 'Nenhuma empresa ainda',
  'Create a company to start multi-tenant administration.': 'Crie uma empresa para iniciar a administração multi-inquilino.',
  'No users yet': 'Nenhum usuário ainda',
  'Create a manager or operator for the active company.': 'Crie um gestor ou operador para a empresa ativa.',
  'No establishments yet': 'Nenhum estabelecimento ainda',
  'Add an establishment, then manage its cameras and prompts.': 'Adicione um estabelecimento e gerencie câmeras e prompts.',
  'No cases yet': 'Nenhum caso ainda',
  'New detections will appear here in real time.': 'Novas detecções aparecerão aqui em tempo real.',
  'Select a case': 'Selecione um caso',
  'Choose an item from the feed to review evidence and resolve.': 'Escolha um item da fila para revisar evidências e resolver.',
  'Live': 'Ao vivo',
  'Disconnected': 'Desconectado',
  'Connecting…': 'Conectando…',
  'Companies': 'Empresas',
  'Users': 'Usuários',
  'Establishments': 'Estabelecimentos',
  'Cameras': 'Câmeras',
  'Prompts': 'Prompts',
  'Prompt set': 'Conjunto de prompts',
  'Webhooks': 'Webhooks',
  'Edit': 'Editar',
  'Delete': 'Excluir',
  'New company': 'Nova empresa',
  'Company created.': 'Empresa criada.',
  'Company name': 'Nome da empresa',
  'Create company': 'Criar empresa',
  'Select a tenant before creating a user.': 'Selecione uma empresa antes de criar um usuário.',
  'User created.': 'Usuário criado.',
  'User email': 'E-mail do usuário',
  'Password': 'Senha',
  'User role': 'Papel do usuário',
  'Manager': 'Gestor',
  'Operator': 'Operador',
  'Create user': 'Criar usuário',
  'New establishment': 'Novo estabelecimento',
  'New camera': 'Nova câmera',
  'Establishment created.': 'Estabelecimento criado.',
  'Establishment name': 'Nome do estabelecimento',
  'Address': 'Endereço',
  'no address': 'sem endereço',
  'Create establishment': 'Criar estabelecimento',
  'Camera name': 'Nome da câmera',
  'Stream URL (RTSP)': 'URL de stream (RTSP)',
  'Add camera': 'Adicionar câmera',
  'No cameras yet': 'Nenhuma câmera ainda',
  'Add a camera with an RTSP stream URL.': 'Adicione uma câmera com URL de stream RTSP.',
  'Cameras · {name}': 'Câmeras · {name}',
  'Close cameras': 'Fechar câmeras',
  'No prompts yet': 'Nenhum prompt ainda',
  'Add prompts that define positive detections.': 'Adicione prompts que definem detecções positivas.',
  'Prompt name': 'Nome do prompt',
  'Prompt body': 'Texto do prompt',
  'Add prompt': 'Adicionar prompt',
  'Edit prompt': 'Editar prompt',
  'Enabled': 'Ativo',
  'Disabled': 'Inativo',
  'Enable': 'Ativar',
  'Disable': 'Desativar',
  'Prompt saved.': 'Prompt salvo.',
  'Prompt created.': 'Prompt criado.',
  'No webhook endpoints yet': 'Nenhum endpoint de webhook ainda',
  'Create an endpoint to receive external context events.': 'Crie um endpoint para receber eventos de contexto externos.',
  'Webhook name': 'Nome do webhook',
  'Create webhook': 'Criar webhook',
  'Webhook created. Copy the token now — it will not be shown again.': 'Webhook criado. Copie o token agora — ele não será exibido novamente.',
  'Token (copy now)': 'Token (copie agora)',
  'Create your account.': 'Crie sua conta.',
  'At least 8 characters.': 'Mínimo de 8 caracteres.',
  'Create account': 'Criar conta',
  'Already have an account?': 'Já tem conta?',
  'No account?': 'Não tem conta?',
  'Register': 'Cadastre-se',
  'This email is already registered.': 'Este e-mail já está cadastrado.',
  'Invalid email or password.': 'E-mail ou senha inválidos.',
  'Password must be at least 8 characters.': 'A senha deve ter pelo menos 8 caracteres.',
  'An error occurred. Please try again.': 'Ocorreu um erro. Tente novamente.',
  'Switch language': 'Mudar idioma',
  'PT-BR': 'PT-BR',
  'Checking session…': 'Verificando sessão…',
  'Redirecting to sign in…': 'Redirecionando para o login…',
  'No company assigned yet.': 'Nenhuma empresa atribuída ainda.',
  'Ask an administrator for access.': 'Peça acesso a um administrador.',
  'Triage': 'Triagem',
  'Real-time workspace': 'Painel em tempo real',
  'Live triage connected.': 'Triagem ao vivo conectada.',
  'WebSocket connection failed.': 'Falha na conexão WebSocket.',
  'WebSocket disconnected; refresh to reconnect.': 'WebSocket desconectado; atualize para reconectar.',
  'Case feed': 'Fila de casos',
  'Detection feed': 'Fila de detecções',
  '{confidence}% confidence': '{confidence}% de confiança',
  'Case updated.': 'Caso atualizado.',
  'Case detail': 'Detalhe do caso',
  'Summary': 'Resumo',
  'Prompt hits': 'Acertos de prompt',
  'Evidence': 'Evidência',
  'No evidence clip or frames.': 'Sem clipe ou frames de evidência.',
  'Disposition': 'Disposição',
  'Reasoning (optional, recommended for false positive)': 'Justificativa (opcional, recomendada para falso positivo)',
  'Reasoning is required for false positive.': 'Justificativa é obrigatória para falso positivo.',
  'Confirm': 'Confirmar',
  'Dismiss': 'Descartar',
  'False positive': 'Falso positivo',
  'Select…': 'Selecione…',
};

const dictionaries: Record<Locale, Record<string, string>> = {
  en: {},
  'pt-BR': ptBR,
};

export function translate(locale: Locale, key: string, vars?: TranslationVars): string {
  let value = locale === 'en' ? key : (dictionaries[locale][key] ?? key);
  if (vars) {
    value = value.replace(/\{(\w+)\}/g, (match, name: string) =>
      name in vars ? String(vars[name]) : match,
    );
  }
  return value;
}

export function localizeApiError(message: string, t: TFunction): string {
  const normalized = message.toLowerCase();
  if (normalized.includes('already registered'))
    return t('This email is already registered.');
  if (normalized.includes('invalid email or password'))
    return t('Invalid email or password.');
  if (normalized.includes('at least 8'))
    return t('Password must be at least 8 characters.');
  return t('An error occurred. Please try again.');
}
