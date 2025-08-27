export type ShowBlockModalMessage = {
  type: 'SHOW_BLOCK_MODAL';
  payload: { url: string; title: string };
};

export type CloseBlockModalMessage = {
  type: 'CLOSE_BLOCK_MODAL';
};

export type RuntimeMessage = ShowBlockModalMessage | CloseBlockModalMessage;
