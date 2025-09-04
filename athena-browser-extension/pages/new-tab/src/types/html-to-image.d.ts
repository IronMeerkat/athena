declare module "html-to-image" {
  export function toBlob(node: HTMLElement): Promise<Blob>;
  export function toPng(node: HTMLElement): Promise<string>;
}

