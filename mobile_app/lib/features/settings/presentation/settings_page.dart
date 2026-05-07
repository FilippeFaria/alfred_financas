import 'package:flutter/material.dart';

import '../../../core/env/app_env.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final flavor = AppEnv.flavor.name;
    final baseUrl = AppEnv.apiBaseUrl;

    return Scaffold(
      appBar: AppBar(title: const Text('Ajustes')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: const Icon(Icons.flag_outlined),
              title: const Text('Ambiente'),
              subtitle: Text(flavor.toUpperCase()),
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.link_outlined),
              title: const Text('API Base URL'),
              subtitle: Text(baseUrl),
            ),
          ),
        ],
      ),
    );
  }
}
