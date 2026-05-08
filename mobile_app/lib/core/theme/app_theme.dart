import 'package:flutter/material.dart';

class AppTheme {
  const AppTheme._();

  static ThemeData get light {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF0E7A6D),
      brightness: Brightness.light,
      surface: const Color(0xFFFFFFFF),
    );

    final baseTextTheme = Typography.material2021().black;

    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: const Color(0xFFF5F8F7),
      colorScheme: colorScheme,
      textTheme: baseTextTheme.copyWith(
        titleLarge: baseTextTheme.titleLarge?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
        headlineSmall: baseTextTheme.headlineSmall?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
        ),
        bodyLarge: baseTextTheme.bodyLarge?.copyWith(
          height: 1.35,
        ),
      ),
      appBarTheme: AppBarTheme(
        centerTitle: false,
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        foregroundColor: colorScheme.onSurface,
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        clipBehavior: Clip.antiAlias,
        margin: EdgeInsets.zero,
        color: colorScheme.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
          side: BorderSide(color: colorScheme.outlineVariant.withOpacity(0.55)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white.withOpacity(0.94),
        elevation: 0,
        indicatorColor: colorScheme.secondaryContainer,
        labelTextStyle: const MaterialStatePropertyAll(
          TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: colorScheme.outlineVariant.withOpacity(0.55)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: colorScheme.primary, width: 1.6),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    );
  }
}
