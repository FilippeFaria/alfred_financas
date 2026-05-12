import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/notifications/local_notification_service.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await LocalNotificationService.instance.initialize();
  runApp(const ProviderScope(child: AlfredApp()));
}

class AlfredApp extends ConsumerStatefulWidget {
  const AlfredApp({super.key});

  @override
  ConsumerState<AlfredApp> createState() => _AlfredAppState();
}

class _AlfredAppState extends ConsumerState<AlfredApp> {
  static const MethodChannel _notificationChannel = MethodChannel('alfred_financas/notifications');
  StreamSubscription<LocalNotificationAction>? _notificationSubscription;

  @override
  void initState() {
    super.initState();
    _abrirRotaPendenteAoIniciar();
    _notificationSubscription = LocalNotificationService.instance.actions.listen((action) {
      if (!mounted) return;
      if (action.type == 'detected_transaction') {
        final pendingId = action.pendingTransactionId?.trim();
        if (pendingId != null && pendingId.isNotEmpty) {
          ref.read(appRouterProvider).go('/insights?from_notification=1&pending_id=$pendingId');
        } else {
          ref.read(appRouterProvider).go('/insights?from_notification=1');
        }
      }
    });
  }

  Future<void> _abrirRotaPendenteAoIniciar() async {
    try {
      final route = await _notificationChannel.invokeMethod<String>('getPendingOpenRoute');
      if (!mounted) return;
      if (route != null && route.isNotEmpty) {
        ref.read(appRouterProvider).go(route);
      }
    } catch (_) {
      // Ignora falha de ponte nativa para nao bloquear inicializacao.
    }
  }

  @override
  void dispose() {
    _notificationSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(appRouterProvider);

    return MaterialApp.router(
      title: 'Alfred Financas',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      routerConfig: router,
    );
  }
}
