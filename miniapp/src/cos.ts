import COS from 'cos-wx-sdk-v5'
import type { UploadAuthorization } from './api'

export function uploadImage(auth: UploadAuthorization, filePath: string, onProgress: (percent: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const cos = new COS({
      SimpleUploadMethod: 'putObject',
      getAuthorization: (_options: unknown, callback: (credentials: unknown) => void) => callback({
        TmpSecretId: auth.credentials.tmpSecretId,
        TmpSecretKey: auth.credentials.tmpSecretKey,
        SecurityToken: auth.credentials.sessionToken,
        StartTime: auth.start_time,
        ExpiredTime: auth.expired_time,
      }),
    })
    cos.putObject({
      Bucket: auth.bucket, Region: auth.region, Key: auth.object_key, FilePath: filePath,
      onProgress: (info: { percent: number }) => onProgress(Math.round(info.percent * 100)),
    }, (error: unknown) => error ? reject(error) : resolve())
  })
}
