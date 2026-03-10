import { createContext, useContext } from 'react';

export type AppMode = 'anthropic' | 'gitlab';
export const ModeContext = createContext<AppMode>('anthropic');
export const useMode = () => useContext(ModeContext);
