class StatusDto {
  StatusDto({required this.status});

  final String status;

  factory StatusDto.fromJson(Map<String, dynamic> json) {
    return StatusDto(status: (json['status'] ?? '').toString());
  }
}
