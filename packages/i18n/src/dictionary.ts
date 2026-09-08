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
  'Location': 'Local',
  'Active location': 'Local ativo',
  'No location selected': 'Nenhum local selecionado',
  'Company context updated.': 'Contexto de empresa atualizado.',
  'Active location: {name}': 'Local ativo: {name}',
  'Location cleared.': 'Local removido.',
  'Signed in as {email} ({role})': 'Conectado como {email} ({role})',
  'Delete {name}?': 'Excluir {name}?',
  'Delete {name}? This cannot be undone.': 'Excluir {name}? Esta ação não pode ser desfeita.',
  'Cancel': 'Cancelar',
  'Save': 'Salvar',
  'Close': 'Fechar',
  'Loading': 'Carregando',
  'Loading decisions': 'Carregando decisões',
  'Delete company': 'Excluir empresa',
  'Edit company': 'Editar empresa',
  'Delete user': 'Excluir usuário',
  'Delete location': 'Excluir local',
  'Edit location': 'Editar local',
  'End your session on this device?': 'Encerrar sua sessão neste dispositivo?',
  'Tenant context': 'Contexto do locatário',
  'No companies yet': 'Nenhuma empresa ainda',
  'Create a company to start multi-tenant administration.': 'Crie uma empresa para iniciar a administração multi-inquilino.',
  'No users yet': 'Nenhum usuário ainda',
  'Create a manager or operator for the active company.': 'Crie um gestor ou operador para a empresa ativa.',
  'No locations yet': 'Nenhum local ainda',
  'Add a location with an optional floor-plan sketch.': 'Adicione um local com planta opcional.',
  'No decisions yet': 'Nenhuma decisão ainda',
  'New detections will appear here in real time.': 'Novas detecções aparecerão aqui em tempo real.',
  'Select a decision': 'Selecione uma decisão',
  'Choose an item from the feed to review evidence and resolve.': 'Escolha um item da fila para revisar evidências e resolver.',
  'Live': 'Ao vivo',
  'Disconnected': 'Desconectado',
  'Connecting…': 'Conectando…',
  'Companies': 'Empresas',
  'Users': 'Usuários',
  'Locations': 'Locais',
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
  'New location': 'Novo local',
  'New camera': 'Nova câmera',
  'Location created.': 'Local criado.',
  'Location name': 'Nome do local',
  'Address (used by the agent)': 'Endereço (usado pelo agente)',
  'Address (agent)': 'Endereço (agente)',
  'no address': 'sem endereço',
  'Sketch': 'Planta',
  '{name} sketch': 'Planta de {name}',
  'No sketch uploaded yet.': 'Nenhuma planta enviada ainda.',
  'Close plan': 'Fechar planta',
  'Plan': 'Planta',
  'Create location': 'Criar local',
  'Sketch uploaded for {name}.': 'Planta enviada para {name}.',
  'Failed to place camera.': 'Falha ao posicionar câmera.',
  'Camera to place': 'Câmera a posicionar',
  'Select camera…': 'Selecione a câmera…',
  'placed': 'posicionada',
  'Click the sketch to place the selected camera.': 'Clique na planta para posicionar a câmera selecionada.',
  'Camera name': 'Nome da câmera',
  'Stream URL (RTSP)': 'URL de stream (RTSP)',
  'Add camera': 'Adicionar câmera',
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
  'Decision feed': 'Fila de decisões',
  '{count} evidence · severity {severity}': '{count} evidência · gravidade {severity}',
  '{count} evidences · severity {severity}': '{count} evidências · gravidade {severity}',
  'Decision resolved.': 'Decisão resolvida.',
  'Decision detail': 'Detalhe da decisão',
  '{count} evidences': '{count} evidências',
  'Disposition': 'Disposição',
  'Select…': 'Selecione…',
  'True Positive': 'Verdadeiro positivo',
  'False Positive': 'Falso positivo',
  'False Negative': 'Falso negativo',
  'Reasoning (required for false positive/negative)': 'Justificativa (obrigatória para falso positivo/negativo)',
  'Resolve': 'Resolver',
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
