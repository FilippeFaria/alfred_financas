import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.link_outlined),
              title: const Text('API Base URL'),
              subtitle: Text(baseUrl),
              trailing: IconButton(
                tooltip: 'Copiar URL',
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: baseUrl));
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('URL copiada para a área de transferência.')),
                    );
                  }
                },
                icon: const Icon(Icons.copy),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Sobre este app',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'O mobile foi pensado para leitura rápida, com foco em dashboard, lançamentos '
                    'e insights. A próxima evolução deve conectar preferências, autenticação e '
                    'sincronização mais fina com o backend.',
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
