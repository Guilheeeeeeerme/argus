import { useTheme } from '../theme';

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className="argus-btn argus-btn--ghost argus-btn--sm"
      onClick={toggle}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  );
}
