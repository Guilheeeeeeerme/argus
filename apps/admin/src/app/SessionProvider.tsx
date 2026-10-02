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
import { isPlatformRole, type Account, type Unit, type Session } from '../api/types';

export interface SessionContextValue {
  /** False until the stored token has been validated (or found absent). */
  booted: boolean;
  session: Session | null;
  accounts: Account[];
  units: Unit[];
  /** True while the lists are refreshing after login or a context switch. */
  loadingContext: boolean;
  /** True while PATCH /v1/auth/context is in flight. */
  switching: boolean;
  isPlatform: boolean;
  setSession: (session: Session | null) => void;
  /** Refetch accounts and units for the active session. */
  reloadContext: () => Promise<void>;
  switchAccount: (id: string | null) => Promise<void>;
  switchUnit: (id: string | null) => Promise<void>;
  signOut: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const t = useT();
  const toast = useToast();
  const [booted, setBooted] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
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
  const activeAccountId = session?.activeAccount?.id ?? null;

  const reloadContext = useCallback(async () => {
    if (!userId) {
      setAccounts([]);
      setUnits([]);
      return;
    }
    setLoadingContext(true);
    try {
      const [accountList, unitList] = await Promise.all([
        auth.accounts(),
        activeAccountId ? unitsApi.list(activeAccountId) : Promise.resolve([] as Unit[]),
      ]);
      setAccounts(accountList);
      setUnits(unitList);
    } catch (error) {
      toast.error(localizeApiError(error, t));
    } finally {
      setLoadingContext(false);
    }
  }, [userId, activeAccountId, toast, t]);

  useEffect(() => {
    void reloadContext();
  }, [reloadContext]);

  const switchAccount = useCallback(
    async (id: string | null) => {
      setSwitching(true);
      try {
        const next = await auth.switchContext({ accountId: id });
        setSession(next);
        const target = returnTo();
        if (target !== APP && next.activeAccount) {
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

  const switchUnit = useCallback(
    async (id: string | null) => {
      setSwitching(true);
      try {
        const next = await auth.switchContext({ unitId: id });
        setSession(next);
        toast.success(
          id
            ? t('Unidade ativa: {name}', { name: next.activeUnit?.name ?? '' })
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
      accounts,
      units,
      loadingContext,
      switching,
      isPlatform: session ? isPlatformRole(session.user.role) : false,
      setSession,
      reloadContext,
      switchAccount,
      switchUnit,
      signOut,
    }),
    [
      booted,
      session,
      accounts,
      units,
      loadingContext,
      switching,
      reloadContext,
      switchAccount,
      switchUnit,
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

/** Active account id, or throws — for routes already guarded by `RequireAccount`. */
export function useAccountId(): string {
  const { session } = useSession();
  const id = session?.activeAccount?.id;
  if (!id) throw new Error('No active account in session');
  return id;
}
