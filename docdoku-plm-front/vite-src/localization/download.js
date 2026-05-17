// download 模块的国际化字符串（ES Module 版）
// 原始来源：app/js/localization/nls/download.js（AMD define）
// 后续可扩展为动态 locale 加载

const strings = {
  en: {
    DOWNLOAD: 'Download',
    DPLM_CLIENT: 'DPLM Client',
    DPLM_CLIENT_INSTALL_MESSAGE: 'DPLM Client is a software that works under Windows, MacOS and Linux.',
    CHOOSE_PLATFORM: 'Choose your platform',
    DPLM_CLIENT_ABOUT_QUESTION: 'What is DPLM Client?',
    DPLM_CLIENT_ABOUT_TEXT:
      'DPLM Client is a multi-platform client application which allows to exchange efficiently (upload / download) files between your local workstation and the DocDokuPLM server. File format agnostic, it provides seamless integration with all the authoring tools on the market.',
  },
  fr: {
    DOWNLOAD: 'Télécharger',
    DPLM_CLIENT: 'Client DPLM',
    DPLM_CLIENT_INSTALL_MESSAGE: 'Le client DPLM est un logiciel compatible Windows, MacOS et Linux.',
    CHOOSE_PLATFORM: 'Choisissez votre plateforme',
    DPLM_CLIENT_ABOUT_QUESTION: 'Qu\'est-ce que le client DPLM ?',
    DPLM_CLIENT_ABOUT_TEXT:
      'Le client DPLM est une application cliente multi-plateforme qui permet d\'échanger efficacement (upload / download) des fichiers entre votre poste local et le serveur DocDokuPLM.',
  },
  zh: {
    DOWNLOAD: '下载',
    DPLM_CLIENT: 'DPLM 客户端',
    DPLM_CLIENT_INSTALL_MESSAGE: 'DPLM 客户端支持 Windows、MacOS 和 Linux 操作系统。',
    CHOOSE_PLATFORM: '选择您的操作系统',
    DPLM_CLIENT_ABOUT_QUESTION: '什么是 DPLM 客户端？',
    DPLM_CLIENT_ABOUT_TEXT:
      'DPLM 客户端是一款跨平台应用，可高效地在本地工作站与 DocDokuPLM 服务器之间传输文件，支持所有主流文件格式。',
  },
}

export default strings
