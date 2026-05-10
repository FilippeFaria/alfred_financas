import 'dart:async';

import 'package:flutter/material.dart';
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
  StreamSubscription<LocalNotificationAction>? _notificationSubscription;

  @override
  void initState() {
    super.initState();
    _notificationSubscription = LocalNotificationService.instance.actions.listen((action) {
      if (!mounted) return;
      if (action.type == 'detected_transaction') {
        ref.read(appRouterProvider).go('/insights');
      }
    });
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
