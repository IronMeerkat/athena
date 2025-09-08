export interface LocaleType {
  WIP: string;
  Error: {
    Unauthorized: string;
  };
  Auth: {
    Return: string;
    Title: string;
    Tips: string;
    SubTips: string;
    Input: string;
    Confirm: string;
    Later: string;
    SaasTips: string;
    TopTips: string;
  };
  ChatItem: {
    ChatItemCount: (count: number) => string;
  };
  Chat: {
    SubTitle: (count: number) => string;
    EditMessage: {
      Title: string;
      Topic: {
        Title: string;
        SubTitle: string;
      };
    };
    Actions: {
      ChatList: string;
      CompressedHistory: string;
      Export: string;
      Copy: string;
      Stop: string;
      Retry: string;
      Pin: string;
      PinToastContent: string;
      PinToastAction: string;
      Delete: string;
      Edit: string;
      FullScreen: string;
      RefreshTitle: string;
      RefreshToast: string;
      Speech: string;
      StopSpeech: string;
    };
    Commands: {
      new: string;
      newm: string;
      next: string;
      prev: string;
      clear: string;
      fork: string;
      del: string;
    };
    InputActions: {
      Stop: string;
      ToBottom: string;
      Theme: {
        auto: string;
        light: string;
        dark: string;
      };
      Prompt: string;
      Masks: string;
      Clear: string;
      Settings: string;
      UploadImage: string;
    };
    Rename: string;
    Typing: string;
    Input: (submitKey: string) => string;
    Send: string;
    StartSpeak: string;
    StopSpeak: string;
    Config: {
      Reset: string;
      SaveAs: string;
    };
    IsContext: string;
    ShortcutKey: {
      Title: string;
      newChat: string;
      focusInput: string;
      copyLastMessage: string;
      copyLastCode: string;
      showShortcutKey: string;
      clearContext: string;
    };
  };
  Export: {
    Title: string;
    Copy: string;
    Download: string;
    MessageFromYou: string;
    MessageFromChatGPT: string;
    Share: string;
    Format: {
      Title: string;
      SubTitle: string;
    };
    IncludeContext: {
      Title: string;
      SubTitle: string;
    };
    Steps: {
      Select: string;
      Preview: string;
    };
    Image: {
      Toast: string;
      Modal: string;
    };
    Artifacts: {
      Title: string;
      Error: string;
    };
  };
  Select: {
    Search: string;
    All: string;
    Latest: string;
    Clear: string;
  };
  Memory: {
    Title: string;
    EmptyContent: string;
    Send: string;
    Copy: string;
    Reset: string;
    ResetConfirm: string;
  };
  Home: {
    NewChat: string;
    DeleteChat: string;
    DeleteToast: string;
    Revert: string;
  };
  Settings: {
    Title: string;
    SubTitle: string;
    ShowPassword: string;
    Danger: {
      Reset: {
        Title: string;
        SubTitle: string;
        Action: string;
        Confirm: string;
      };
      Clear: {
        Title: string;
        SubTitle: string;
        Action: string;
        Confirm: string;
      };
    };
    Lang: {
      Name: string;
      All: string;
    };
    Avatar: string;
    FontSize: {
      Title: string;
      SubTitle: string;
    };
    FontFamily: {
      Title: string;
      SubTitle: string;
      Placeholder: string;
    };
    InjectSystemPrompts: {
      Title: string;
      SubTitle: string;
    };
    InputTemplate: {
      Title: string;
      SubTitle: string;
    };
    Update: {
      Version: (x: string) => string;
      IsLatest: string;
      CheckUpdate: string;
      IsChecking: string;
      FoundUpdate: (x: string) => string;
      GoToUpdate: string;
      Success: string;
      Failed: string;
    };
    SendKey: string;
    Theme: string;
    TightBorder: string;
    SendPreviewBubble: {
      Title: string;
      SubTitle: string;
    };
    AutoGenerateTitle: {
      Title: string;
      SubTitle: string;
    };
    Sync: {
      CloudState: string;
      NotSyncYet: string;
      Success: string;
      Fail: string;
      Config: {
        Modal: {
          Title: string;
          Check: string;
        };
        SyncType: {
          Title: string;
          SubTitle: string;
        };
        Proxy: {
          Title: string;
          SubTitle: string;
        };
        ProxyUrl: {
          Title: string;
          SubTitle: string;
        };
        WebDav: {
          Endpoint: string;
          UserName: string;
          Password: string;
        };
        UpStash: {
          Endpoint: string;
          UserName: string;
          Password: string;
        };
      };
      LocalState: string;
      Overview: (overview: { chat: number; message: number; prompt: number; mask: number }) => string;
      ImportFailed: string;
    };
    Mask: {
      Splash: {
        Title: string;
        SubTitle: string;
      };
      Builtin: {
        Title: string;
        SubTitle: string;
      };
    };
    Prompt: {
      Disable: {
        Title: string;
        SubTitle: string;
      };
      List: string;
      ListCount: (builtin: number, custom: number) => string;
      Edit: string;
      Modal: {
        Title: string;
        Add: string;
        Search: string;
      };
      EditModal: {
        Title: string;
      };
    };
    HistoryCount: {
      Title: string;
      SubTitle: string;
    };
    CompressThreshold: {
      Title: string;
      SubTitle: string;
    };
    Usage: {
      Title: string;
      SubTitle: (used: number, total: number) => string;
      IsChecking: string;
      Check: string;
      NoAccess: string;
    };
    Access: {
      SaasStart: {
        Title: string;
        Label: string;
        SubTitle: string;
        ChatNow: string;
      };
      AccessCode: {
        Title: string;
        SubTitle: string;
        Placeholder: string;
      };
      CustomEndpoint: {
        Title: string;
        SubTitle: string;
      };
      Provider: {
        Title: string;
        SubTitle: string;
      };
      OpenAI: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      Azure: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
        ApiVerion: {
          Title: string;
          SubTitle: string;
        };
      };
      Anthropic: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
        ApiVerion: {
          Title: string;
          SubTitle: string;
        };
      };
      Baidu: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        SecretKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      Tencent: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        SecretKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      ByteDance: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      Alibaba: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      Moonshot: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      DeepSeek: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      XAI: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      ChatGLM: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      SiliconFlow: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      Stability: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      Iflytek: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        ApiSecret: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
      CustomModel: {
        Title: string;
        SubTitle: string;
      };
      Google: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
        ApiVersion: {
          Title: string;
          SubTitle: string;
        };
        GoogleSafetySettings: {
          Title: string;
          SubTitle: string;
        };
      };
      AI302: {
        ApiKey: {
          Title: string;
          SubTitle: string;
          Placeholder: string;
        };
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
      };
    };
    Model: string;
    CompressModel: {
      Title: string;
      SubTitle: string;
    };
    Temperature: {
      Title: string;
      SubTitle: string;
    };
    TopP: {
      Title: string;
      SubTitle: string;
    };
    MaxTokens: {
      Title: string;
      SubTitle: string;
    };
    PresencePenalty: {
      Title: string;
      SubTitle: string;
    };
    FrequencyPenalty: {
      Title: string;
      SubTitle: string;
    };
    TTS: {
      Enable: {
        Title: string;
        SubTitle: string;
      };
      Autoplay: {
        Title: string;
        SubTitle: string;
      };
      Model: string;
      Voice: {
        Title: string;
        SubTitle: string;
      };
      Speed: {
        Title: string;
        SubTitle: string;
      };
      Engine: string;
    };
    Realtime: {
      Enable: {
        Title: string;
        SubTitle: string;
      };
      Provider: {
        Title: string;
        SubTitle: string;
      };
      Model: {
        Title: string;
        SubTitle: string;
      };
      ApiKey: {
        Title: string;
        SubTitle: string;
        Placeholder: string;
      };
      Azure: {
        Endpoint: {
          Title: string;
          SubTitle: string;
        };
        Deployment: {
          Title: string;
          SubTitle: string;
        };
      };
      Temperature: {
        Title: string;
        SubTitle: string;
      };
    };
  };
  Store: {
    DefaultTopic: string;
    BotHello: string;
    Error: string;
    Prompt: {
      History: (content: string) => string;
      Topic: string;
      Summarize: string;
    };
  };
  Copy: {
    Success: string;
    Failed: string;
  };
  Download: {
    Success: string;
    Failed: string;
  };
  Context: {
    Toast: (x: string | number) => string;
    Edit: string;
    Add: string;
    Clear: string;
    Revert: string;
  };
  Discovery: {
    Name: string;
  };
  Mcp: {
    Name: string;
  };
  FineTuned: {
    Sysmessage: string;
  };
  SearchChat: {
    Name: string;
    Page: {
      Title: string;
      Search: string;
      NoResult: string;
      NoData: string;
      Loading: string;
      SubTitle: (count: number) => string;
    };
    Item: {
      View: string;
    };
  };
  Plugin: {
    Name: string;
    Page: {
      Title: string;
      SubTitle: (count: number) => string;
      Search: string;
      Create: string;
      Find: string;
    };
    Item: {
      Info: (count: number) => string;
      View: string;
      Edit: string;
      Delete: string;
      DeleteConfirm: string;
    };
    Auth: {
      None: string;
      Basic: string;
      Bearer: string;
      Custom: string;
      CustomHeader: string;
      Token: string;
      Proxy: string;
      ProxyDescription: string;
      Location: string;
      LocationHeader: string;
      LocationQuery: string;
      LocationBody: string;
    };
    EditModal: {
      Title: (readonly: boolean) => string;
      Download: string;
      Auth: string;
      Content: string;
      Load: string;
      Method: string;
      Error: string;
    };
  };
  Mask: {
    Name: string;
    Page: {
      Title: string;
      SubTitle: (count: number) => string;
      Search: string;
      Create: string;
    };
    Item: {
      Info: (count: number) => string;
      Chat: string;
      View: string;
      Edit: string;
      Delete: string;
      DeleteConfirm: string;
    };
    EditModal: {
      Title: (readonly: boolean) => string;
      Download: string;
      Clone: string;
    };
    Config: {
      Avatar: string;
      Name: string;
      Sync: {
        Title: string;
        SubTitle: string;
        Confirm: string;
      };
      HideContext: {
        Title: string;
        SubTitle: string;
      };
      Artifacts: {
        Title: string;
        SubTitle: string;
      };
      CodeFold: {
        Title: string;
        SubTitle: string;
      };
      Share: {
        Title: string;
        SubTitle: string;
        Action: string;
      };
    };
  };
  NewChat: {
    Return: string;
    Skip: string;
    Title: string;
    SubTitle: string;
    More: string;
    NotShow: string;
    ConfirmNoShow: string;
  };
  UI: {
    Confirm: string;
    Cancel: string;
    Close: string;
    Create: string;
    Edit: string;
    Export: string;
    Import: string;
    Sync: string;
    Config: string;
  };
  Exporter: {
    Description: {
      Title: string;
    };
    Model: string;
    Messages: string;
    Topic: string;
    Time: string;
  };
  URLCommand: {
    Code: string;
    Settings: string;
  };
  SdPanel: {
    Prompt: string;
    NegativePrompt: string;
    PleaseInput: (name: string) => string;
    AspectRatio: string;
    ImageStyle: string;
    OutFormat: string;
    AIModel: string;
    ModelVersion: string;
    Submit: string;
    ParamIsRequired: (name: string) => string;
    Styles: {
      D3Model: string;
      AnalogFilm: string;
      Anime: string;
      Cinematic: string;
      ComicBook: string;
      DigitalArt: string;
      Enhance: string;
      FantasyArt: string;
      Isometric: string;
      LineArt: string;
      LowPoly: string;
      ModelingCompound: string;
      NeonPunk: string;
      Origami: string;
      Photographic: string;
      PixelArt: string;
      TileTexture: string;
    };
  };
  Sd: {
    SubTitle: (count: number) => string;
    Actions: {
      Params: string;
      Copy: string;
      Delete: string;
      Retry: string;
      ReturnHome: string;
      History: string;
    };
    EmptyRecord: string;
    Status: {
      Name: string;
      Success: string;
      Error: string;
      Wait: string;
      Running: string;
    };
    Danger: {
      Delete: string;
    };
    GenerateParams: string;
    Detail: string;
  };
}

export type PartialLocaleType = Partial<LocaleType>;


