import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useToast } from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { clearToken, consumeTokenFromUrl, getToken } from '@shared/auth';
import { auth, units as unitsApi, APP, returnTo, withToken } from '../api/client';
import { isPlatformRole, type Company, type Establishment, type Session } from '../api/types';

export interface SessionContextValue {
  /** False until the stored token has been validated (or found absent). */
  booted: boolean;
  session: Session | null;
  companies: Company[];
  establishments: Establishment[];
  /** True while the lists are refreshing after login or a context switch. */
  loadingContext: boolean;
  /** True while PATCH /v1/auth/context is in flight. */
  switching: boolean;
  isPlatform: boolean;
  setSession: (session: Session | null) => void;
  /** Refetch companies and establishments for the active session. */
  reloadContext: () => Promise<void>;
  switchCompany: (id: string | null) => Promise<void>;
  switchEstablishment: (id: string | null) => Promise<void>;
  signOut: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const t = useT();
  const toast = useToast();
  const [booted, setBooted] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [establishments, setEstablishments] = useState<Establishment[]>([]);
  const [loadingContext, setLoadingContext] = useState(false);
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    consumeTokenFromUrl();
    if (window.location.pathname === '/sso/handoff') {
      setBooted(true);
      return;
    }
    if (!getToken()) {
      setBooted(true);
      return;
    }
    auth
      .me()
      .then(setSession)
      .catch(() => clearToken())
      .finally(() => setBooted(true));
  }, []);

  const userId = session?.user.id ?? null;
  const activeCompanyId = session?.activeCompany?.id ?? null;

  const reloadContext = useCallback(async () => {
    if (!userId) {
      setCompanies([]);
      setEstablishments([]);
      return;
    }
    setLoadingContext(true);
    try {
      const [companyList, unitList] = await Promise.all([
        auth.companies(),
        activeCompanyId ? unitsApi.list(activeCompanyId) : Promise.resolve([] as Establishment[]),
      ]);
      setCompanies(companyList);
      setEstablishments(unitList);
    } catch (error) {
      toast.error(localizeApiError(error, t));
    } finally {
      setLoadingContext(false);
    }
  }, [userId, activeCompanyId, toast, t]);

  useEffect(() => {
    void reloadContext();
  }, [reloadContext]);

  const switchCompany = useCallback(
    async (id: string | null) => {
      setSwitching(true);
      try {
        const next = await auth.switchContext({ companyId: id });
        setSession(next);
        const target = returnTo();
        if (target !== APP && next.activeCompany) {
          window.location.assign(withToken(target));
          return;
        }
        toast.success(t('Conta atualizada.'));
      } catch (error) {
        toast.error(localizeApiError(error, t));
      } finally {
        setSwitching(false);
      }
    },
    [toast, t],
  );

  const switchEstablishment = useCallback(
    async (id: string | null) => {
      setSwitching(true);
      try {
        const next = await auth.switchContext({ establishmentId: id });
        setSession(next);
        toast.success(
          id
            ? t('Unidade ativa: {name}', { name: next.activeEstablishment?.name ?? '' })
            : t('Unidade removida.'),
        );
      } catch (error) {
        toast.error(localizeApiError(error, t));
      } finally {
        setSwitching(false);
      }
    },
    [toast, t],
  );

  const signOut = useCallback(() => {
    void auth.logout().catch(() => undefined);
    clearToken();
    window.location.assign(APP);
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      booted,
      session,
      companies,
      establishments,
      loadingContext,
      switching,
      isPlatform: session ? isPlatformRole(session.user.role) : false,
      setSession,
      reloadContext,
      switchCompany,
      switchEstablishment,
      signOut,
    }),
    [
      booted,
      session,
      companies,
      establishments,
      loadingContext,
      switching,
      reloadContext,
      switchCompany,
      switchEstablishment,
      signOut,
    ],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx;
}

/** Active company id, or throws — for routes already guarded by `RequireCompany`. */
export function useCompanyId(): string {
  const { session } = useSession();
  const id = session?.activeCompany?.id;
  if (!id) throw new Error('No active company in session');
  return id;
}
