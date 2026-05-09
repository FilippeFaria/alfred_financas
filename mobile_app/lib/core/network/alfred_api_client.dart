import 'package:dio/dio.dart';

import 'api_exception.dart';
import 'dto/analise_resumo_dto.dart';
import 'dto/categorias_dto.dart';
import 'dto/criar_transacao_dto.dart';
import 'dto/dashboard_snapshot_dto.dart';
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
    return getTransacoesPaginado(limite: limite ?? 30);
  }

  Future<TransacoesResponseDto> getTransacoesPaginado({
    int pagina = 1,
    int limite = 30,
    String? dataInicio,
    String? dataFim,
    String? categoria,
    String? conta,
    String? tipo,
  }) async {
    try {
      final queryParameters = <String, dynamic>{
        'pagina': pagina,
        'limite': limite,
      };
      if (dataInicio != null && dataInicio.isNotEmpty) {
        queryParameters['data_inicio'] = dataInicio;
      }
      if (dataFim != null && dataFim.isNotEmpty) {
        queryParameters['data_fim'] = dataFim;
      }
      if (categoria != null && categoria.isNotEmpty) {
        queryParameters['categoria'] = categoria;
      }
      if (conta != null && conta.isNotEmpty) {
        queryParameters['conta'] = conta;
      }
      if (tipo != null && tipo.isNotEmpty) {
        queryParameters['tipo'] = tipo;
      }
      final response = await _dio.get(
        '/transacoes',
        queryParameters: queryParameters,
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

  Future<TransacaoDto> postTransacao(CriarTransacaoRequestDto payload) async {
    try {
      final response = await _dio.post('/transacoes', data: payload.toJson());
      return TransacaoDto.fromJson(_asMap(response.data));
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<TransacaoDto> putTransacao(int id, CriarTransacaoRequestDto payload) async {
    try {
      final response = await _dio.put('/transacoes/$id', data: payload.toJson());
      return TransacaoDto.fromJson(_asMap(response.data));
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<void> deleteTransacao(int id) async {
    try {
      await _dio.delete('/transacoes/$id');
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<void> patchTransacaoFlags(
    int id, {
    bool? desconsiderar,
    bool? grandeTransacao,
  }) async {
    try {
      await _dio.patch(
        '/transacoes/$id/flags',
        data: {
          if (desconsiderar != null) 'desconsiderar': desconsiderar,
          if (grandeTransacao != null) 'grande_transacao': grandeTransacao,
        },
      );
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<DashboardSnapshotDto> getDashboardSnapshot({
    required bool desconsiderar,
    required bool va,
    required bool vr,
    required bool bianca,
    required bool filippe,
    required bool dayToDate,
    int? anomeReferencia,
    String? categoria,
    int mesesHistorico = 6,
  }) async {
    try {
      final queryParameters = <String, dynamic>{
        'desconsiderar': desconsiderar,
        'va': va,
        'vr': vr,
        'bianca': bianca,
        'filippe': filippe,
        'day_to_date': dayToDate,
        'meses_historico': mesesHistorico,
      };
      if (anomeReferencia != null) {
        queryParameters['anome_referencia'] = anomeReferencia;
      }
      if (categoria != null && categoria.trim().isNotEmpty) {
        queryParameters['categoria'] = categoria.trim();
      }
      final response = await _dio.get(
        '/mobile/dashboard_snapshot',
        queryParameters: queryParameters,
      );
      return DashboardSnapshotDto.fromJson(_asMap(response.data));
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<Map<String, dynamic>> getOrcamentoValores() async {
    try {
      final response = await _dio.get('/orcamento/valores');
      return _asMap(response.data);
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }

  Future<Map<String, dynamic>> postOrcamentoValores({
    required List<Map<String, dynamic>> items,
  }) async {
    try {
      final response = await _dio.post(
        '/orcamento/valores',
        data: {'items': items},
      );
      return _asMap(response.data);
    } on DioException catch (exception) {
      _throwFromDio(exception);
    }
  }
}
