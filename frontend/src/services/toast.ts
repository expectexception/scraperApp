export type AppToastLevel = 'success' | 'error' | 'info';

export type AppToastPayload = {
    message: string;
    level?: AppToastLevel;
    durationMs?: number;
};

export const APP_TOAST_EVENT = 'aeroops:toast';

export const emitAppToast = (payload: AppToastPayload) => {
    window.dispatchEvent(new CustomEvent<AppToastPayload>(APP_TOAST_EVENT, { detail: payload }));
};
