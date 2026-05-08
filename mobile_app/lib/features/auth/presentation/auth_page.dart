import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class AuthPage extends StatelessWidget {
  const AuthPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Login')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const CircleAvatar(
                      radius: 28,
                      backgroundColor: Color(0xFF0E7A6D),
                      child: Icon(Icons.lock_outline, color: Colors.white),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Autenticação em construção',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Nesta etapa, o acesso continua livre para facilitar os testes internos. '
                      'Quando o login entrar, esta tela vai concentrar a entrada segura no app.',
                    ),
                    const SizedBox(height: 20),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.tonalIcon(
                        onPressed: () => context.go('/dashboard'),
                        icon: const Icon(Icons.arrow_forward),
                        label: const Text('Ir para o dashboard'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
