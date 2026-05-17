/**
 * OIDC 登录工具（ES Module 版）
 * 原：app/js/common-objects/oidc.js
 * 原版通过 shim 依赖 window.Oidc 全局，此处直接从 bower_components/oidc-client ES 模块导入
 */
// 使用 npm 版 oidc-client（含完整 src/，可被 Vite 正确解析）
import OidcLib from 'oidc-client'

// npm 版 main 指向 lib/oidc-client.min.js（UMD），默认导出整个命名空间对象
const UserManager = OidcLib.UserManager || OidcLib.default?.UserManager || OidcLib

function login(provider) {
  var state = provider.name
  var keys
  if (provider.signingKeys) {
    try {
      keys = JSON.parse(provider.signingKeys)
    } catch (e) {
      keys = null
    }
  }

  var settings = {
    authority: provider.authority,
    client_id: provider.clientID,
    id_token_signed_response_alg: provider.jwsAlgorithm,
    redirect_uri: provider.redirectUri,
    response_types: [provider.responseType],
    scope: [provider.scope],
    metadata: {
      issuer: provider.issuer,
      authorization_endpoint: provider.authorizationEndpoint,
      jwks_uri: provider.jwkSetURL
    },
    signingKeys: keys,
    grant_types: ['implicit', 'authorization_code'],
    subject_type: 'public',
    mutual_tls_sender_constrained_access_tokens: false,
    application_type: 'web',
    token_endpoint_auth_method: 'client_secret_basic'
  }

  return new UserManager(settings).signinPopup({ state: state })
}

export default {
  login: login,
  algorithms: ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512', 'ES256',
    'ES384', 'ES512', 'PS256', 'PS384', 'PS512', 'EdDSA']
}
