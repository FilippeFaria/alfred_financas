import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../env/app_env.dart';
import 'alfred_api_client.dart';
import 'interceptors/retry_interceptor.dart';

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: AppEnv.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 20),
      sendTimeout: const Duration(seconds: 20),
    ),
  );

  dio.interceptors.add(RetryInterceptor(dio: dio));
  if (AppEnv.flavor == AppFlavor.dev) {
    dio.interceptors.add(
      LogInterceptor(
        requestBody: true,
        responseBody: true,
      ),
    );
  }

  return dio;
});

final alfredApiClientProvider = Provider<AlfredApiClient>((ref) {
  return AlfredApiClient(ref.watch(dioProvider));
});
