declare global {
  namespace JSX {
    type Element = any;
    interface IntrinsicElements { [elemName: string]: any }
  }
}

