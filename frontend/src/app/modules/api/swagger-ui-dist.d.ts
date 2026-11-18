// This is a minimalist subset type of `@types/swagger-ui-dist` specific to the SEED usage that fixes `requestInterceptor`
declare module 'swagger-ui-dist/swagger-ui-es-bundle' {
  type Request = Record<string, unknown>

  interface SwaggerUIOptions {
    [key: string]: unknown;
    dom_id: string;
    spec: Record<string, unknown>;
    requestInterceptor: (request: Request) => Request | Promise<Request>;
  }

  export default function SwaggerUI(options: SwaggerUIOptions): void
}
