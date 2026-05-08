import 'package:alfred_financas_mobile/core/router/app_router.dart';
import 'package:alfred_financas_mobile/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

void main() {
  testWidgets('renderiza a estrutura base do app', (WidgetTester tester) async {
    final router = GoRouter(
      initialLocation: '/dashboard',
      routes: [
        GoRoute(
          path: '/dashboard',
          builder: (context, state) => const Scaffold(
            body: Center(child: Text('Dashboard de teste')),
          ),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          appRouterProvider.overrideWithValue(router),
        ],
        child: const AlfredApp(),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Dashboard de teste'), findsOneWidget);
  });
}
