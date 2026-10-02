import { useMemo, useState } from 'react';
import { isApiError, type FieldErrors } from '@shared/auth';

/** Merge local validation errors with `ApiError.fieldErrors` from the last failed mutation. */
export function useFieldErrors(mutationError: unknown) {
  const [local, setLocal] = useState<FieldErrors>({});
  const merged = useMemo<FieldErrors>(
    () => ({ ...(isApiError(mutationError) ? mutationError.fieldErrors : {}), ...local }),
    [mutationError, local],
  );
  return { fieldErrors: merged, setLocalErrors: setLocal };
}

/** True when the error carries field-level detail that the form already shows. */
export function hasFieldErrors(error: unknown): boolean {
  return isApiError(error) && Object.keys(error.fieldErrors).length > 0;
}
