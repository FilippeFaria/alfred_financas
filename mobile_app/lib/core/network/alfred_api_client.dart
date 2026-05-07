import 'package:dio/dio.dart';

import 'api_exception.dart';
import 'dto/analise_resumo_dto.dart';
import 'dto/categorias_dto.dart';
import 'dto/saldo_dto.dart';
import 'dto/status_dto.dart';
import 'dto/transacao_dto.dart';

class AlfredApiClient {
  AlfredApiClient(this._dio);

  final Dio _dio;

  Map<String, dynamic> _asMap(dynamic raw) {
    if (raw is Map<String, dynamic>) {
      return raw;
    }
    if (raw is Map) {
      return Map<String, dynamic>.from(raw);
    }
    throw ApiException(message: 'Resposta invalida da API: era esperado um objeto JSON.');
  }

  List<dynamic> _asList(dynamic raw) {
    if (raw is List) {
      return raw;
    }
    throw ApiException(message: 'Resposta invalida da API: era esperado uma lista JSON.');
  }

  Never _throwFromDio(DioException exception) {
    final response = exception.response;
    final responseData = response?.data;

    if (responseData is Map && responseData['error'] is Map) {
      final errorMap = Map<String, dynamic>.from(responseData['error'] as Map);
      throw ApiException(
        message: (errorMap['message'] ?? 'Falha na comunicacao com a API.').toString(),
        statusCode: response?.statusCode,
        code: errorMap['code']?.toString(),
        details: errorMap['details'] is Map
            ? Map<String, dynamic>.from(errorMap['details'] as Map)
            : null,
      );
    }

    if (exception.type == DioExceptionType.connectionTimeout ||
        exception.type == DioExceptionType.receiveTimeout ||
        exception.type == DioExceptionType.sendTimeout) {
      throw ApiException(
        message: 'Timeout ao conectar com a API.',
        statusCode: response?.statusCode,
      );
    }

    throw ApiException(
      message: exception.message ?? 'Erro inesperado ao chamar API.',
      statusCode: response?.statusCode,
    );
  }

  Future<StatusDto> getHealth() async {
    try {
      final response = await _dio.get('/health');
      return StatusDto.fromJson(_asMap(response.data));
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<List<SaldoDto>> getSaldo() async {
    try {
      final response = await _dio.get('/saldo');
      final list = _asList(response.data);
      return list.map((item) => SaldoDto.fromJson(_asMap(item))).toList();
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<TransacoesResponseDto> getTransacoes({int? limite}) async {
    try {
      final response = await _dio.get(
        '/transacoes',
        queryParameters: limite != null ? {'limite': limite} : null,
      );
      return TransacoesResponseDto.fromJson(_asMap(response.data));
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<CategoriasDto> getCategorias() async {
    try {
      final response = await _dio.get('/categorias');
      return CategoriasDto.fromJson(_asMap(response.data));
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<AnaliseResumoDto> postAnaliseResumo(AnaliseResumoRequestDto payload) async {
    try {
      final response = await _dio.post('/analise/resumo', data: payload.toJson());
      return AnaliseResumoDto.fromJson(_asMap(response.data));
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }
}
