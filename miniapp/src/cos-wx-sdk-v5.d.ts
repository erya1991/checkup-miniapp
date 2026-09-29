declare module 'cos-wx-sdk-v5' {
  export default class COS {
    constructor(options: { SimpleUploadMethod: string; getAuthorization: (options: unknown, callback: (credentials: unknown) => void) => void })
    putObject(options: { Bucket: string; Region: string; Key: string; FilePath: string; onProgress: (info: { percent: number }) => void }, callback: (error: unknown) => void): void
  }
}
