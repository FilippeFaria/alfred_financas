enum AppFlavor { dev, prod }

class AppEnv {
  const AppEnv._();

  static AppFlavor get flavor {
    const raw = String.fromEnvironment('FLAVOR', defaultValue: 'dev');
    return raw.toLowerCase() == 'prod' ? AppFlavor.prod : AppFlavor.dev;
  }

  static String get apiBaseUrl {
    const fromDefine = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (fromDefine.isNotEmpty) {
      return fromDefine;
    }

    return switch (flavor) {
      AppFlavor.dev => 'http://10.0.2.2:8000',
      AppFlavor.prod => 'https://api.alfred-financas.com',
    };
  }
}
