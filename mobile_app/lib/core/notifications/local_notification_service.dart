import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LocalNotificationAction {
  LocalNotificationAction({
    required this.type,
    this.pendingTransactionId,
  });

  final String type;
  final String? pendingTransactionId;
}

class LocalNotificationService {
  LocalNotificationService._();

  static final LocalNotificationService instance = LocalNotificationService._();

  static const String channelId = 'alfred_detected_transactions';
  static const String channelName = 'Transacoes detectadas';
  static const String channelDescription =
      'Notificacoes enviadas quando o Alfred identifica uma possivel transacao automaticamente';
  static const String _seenPendingIdsKey = 'seen_detected_pending_notification_ids';

  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  final StreamController<LocalNotificationAction> _actionController = StreamController.broadcast();

  bool _initialized = false;

  Stream<LocalNotificationAction> get actions => _actionController.stream;

  Future<void> initialize() async {
    if (_initialized) return;

    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const settings = InitializationSettings(android: android);

    await _plugin.initialize(
      settings,
      onDidReceiveNotificationResponse: _onDidReceiveNotificationResponse,
      onDidReceiveBackgroundNotificationResponse: _onDidReceiveBackgroundNotificationResponse,
    );

    _initialized = true;
  }

  Future<bool> requestPermission() async {
    if (defaultTargetPlatform != TargetPlatform.android) return true;
    final android = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    return await android?.requestNotificationsPermission() ?? false;
  }

  Future<bool> areNotificationsEnabled() async {
    if (defaultTargetPlatform != TargetPlatform.android) return false;
    final android = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    return await android?.areNotificationsEnabled() ?? false;
  }

  Future<void> showDetectedTransactionNotification({
    required String pendingTransactionId,
    required String conta,
    String? nome,
    double? valor,
    double? confidence,
  }) async {
    final enabled = await areNotificationsEnabled();
    if (!enabled) {
      final granted = await requestPermission();
      if (!granted) return;
    }

    final seen = await _getSeenPendingIds();
    if (seen.contains(pendingTransactionId)) return;

    final valorLabel = valor == null ? 'Nova transacao detectada' : 'R\$ ${valor.toStringAsFixed(2)}';
    final nomeLabel = (nome == null || nome.trim().isEmpty) ? 'transacao' : nome.trim();
    final contaLabel = conta.trim().isEmpty ? 'conta desconhecida' : conta.trim();
    final body = '$valorLabel em $nomeLabel - $contaLabel\nToque para revisar';

    final details = NotificationDetails(
      android: AndroidNotificationDetails(
        channelId,
        channelName,
        channelDescription: channelDescription,
        importance: Importance.high,
        priority: Priority.high,
      ),
    );

    final payload = jsonEncode({
      'type': 'detected_transaction',
      'pending_transaction_id': pendingTransactionId,
    });

    await _plugin.show(
      pendingTransactionId.hashCode,
      'Nova transacao detectada',
      body,
      details,
      payload: payload,
    );

    seen.add(pendingTransactionId);
    await _saveSeenPendingIds(seen);
  }

  Future<void> showDebugNotification() async {
    final enabled = await areNotificationsEnabled();
    if (!enabled) {
      final granted = await requestPermission();
      if (!granted) return;
    }

    final details = NotificationDetails(
      android: AndroidNotificationDetails(
        channelId,
        channelName,
        channelDescription: channelDescription,
        importance: Importance.high,
        priority: Priority.high,
      ),
    );

    await _plugin.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      'Alfred Financas',
      'Teste de notificacao local - se voce viu isso, o canal esta funcionando.',
      details,
      payload: jsonEncode({'type': 'detected_transaction'}),
    );
  }

  Future<Set<String>> _getSeenPendingIds() async {
    final prefs = await SharedPreferences.getInstance();
    final list = prefs.getStringList(_seenPendingIdsKey) ?? const <String>[];
    return list.where((item) => item.trim().isNotEmpty).toSet();
  }

  Future<void> _saveSeenPendingIds(Set<String> ids) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_seenPendingIdsKey, ids.toList()..sort());
  }

  void _onDidReceiveNotificationResponse(NotificationResponse response) {
    final action = _parseAction(response.payload);
    if (action != null) {
      _actionController.add(action);
    }
  }

  @pragma('vm:entry-point')
  static void _onDidReceiveBackgroundNotificationResponse(NotificationResponse response) {
    // No-op: navegação é tratada no fluxo foreground ao abrir app.
  }

  LocalNotificationAction? _parseAction(String? payload) {
    if (payload == null || payload.trim().isEmpty) return null;
    try {
      final map = jsonDecode(payload);
      if (map is! Map) return null;
      final data = Map<String, dynamic>.from(map);
      return LocalNotificationAction(
        type: (data['type'] ?? '').toString(),
        pendingTransactionId: data['pending_transaction_id']?.toString(),
      );
    } catch (_) {
      return null;
    }
  }
}
