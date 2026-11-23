"""Helpers cho KPI AI AdventureWorks.

Các số KPI được kiểm tra đối chiếu với JSON nguồn; không coi văn bản AI
là nguồn sự thật. Đây là kiểm chứng có giới hạn, không thay thế rà soát BI.
"""
import json
import math
import re
from datetime import date, datetime
from decimal import Decimal


def json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, 'item'):
        return value.item()
    return value


def to_json(payload):
    return json.dumps(payload, ensure_ascii=False, default=json_safe, allow_nan=False)


def sql_string(value):
    return "N'" + str(value).replace("'", "''") + "'"


_DATE_PATTERNS = [
    ('ymd', re.compile(r'(?<!\d)(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?!\d)')),
    ('dmy', re.compile(r'(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)')),
    ('month_words', re.compile(r'\btháng\s+(\d{1,2})\s+(?:năm\s+)?(\d{4})\b', re.I)),
    ('ym', re.compile(r'(?<!\d)(\d{4})[-/](\d{1,2})(?![\d/-])')),
    ('my', re.compile(r'(?<![\d/-])(\d{1,2})[-/](\d{4})(?!\d)')),
]

_TOKEN_PATTERN = re.compile(
    r'(?<![\w])[-+]?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?(?!\w)'
    r'|(?<![\w])[-+]?\d+(?:[.,]\d+)?(?!\w)'
)
_PERCENT_SUFFIX = re.compile(r'^\s*(?:%|phần\s+trăm\b|phần\s+trăm\s+điểm\b)', re.I)
_DIRECTION_PREFIX = re.compile(
    r'\b(giảm|sụt\s+giảm|sụt|thấp\s+hơn|tăng|tăng\s+trưởng|cao\s+hơn)\b'
    r'([^.!?;:\d]*)$', re.I
)
_MOM = re.compile(r'\b(?:tháng\s+trước|tháng\s+liền\s+trước|so\s+với\s+tháng\s+trước|mom)\b', re.I)
_YOY = re.compile(r'\b(?:cùng\s+kỳ|năm\s+trước|so\s+với\s+cùng\s+kỳ|yoy)\b', re.I)


def _collect_periods(payload):
    days, months = set(), set()

    def walk(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, (str, date, datetime)):
            s = str(obj)
            match = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?', s)
            if match:
                y, m, d = map(int, match.groups())
                try:
                    day = date(y, m, d)
                except ValueError:
                    return
                days.add(day.isoformat())
                months.add((y, m))
            else:
                match = re.fullmatch(r'(\d{4})-(\d{2})', s)
                if match:
                    y, m = map(int, match.groups())
                    if 1 <= m <= 12:
                        months.add((y, m))

    walk(payload)
    return days, months


def _strip_and_check_dates(text, payload):
    days, months = _collect_periods(payload)
    invalid = []
    clean = text
    for kind, pattern in _DATE_PATTERNS:
        def replace(match):
            try:
                if kind == 'ymd':
                    y, m, d = map(int, match.groups())
                    valid = date(y, m, d).isoformat() in days
                elif kind == 'dmy':
                    d, m, y = map(int, match.groups())
                    valid = date(y, m, d).isoformat() in days
                elif kind in ('month_words', 'my'):
                    m, y = map(int, match.groups())
                    valid = (y, m) in months
                else:
                    y, m = map(int, match.groups())
                    valid = (y, m) in months
            except ValueError:
                valid = False
            if not valid:
                invalid.append(match.group(0))
            return ' '
        clean = pattern.sub(replace, clean)
    return clean, invalid


def _parse_number(token):
    s = token.strip()
    if ',' in s and '.' in s:
        decimal_sep = ',' if s.rfind(',') > s.rfind('.') else '.'
        group_sep = '.' if decimal_sep == ',' else ','
        s = s.replace(group_sep, '').replace(decimal_sep, '.')
    elif re.fullmatch(r'[-+]?\d{1,3}(?:,\d{3})+', s):
        s = s.replace(',', '')
    elif re.fullmatch(r'[-+]?\d{1,3}(?:\.\d{3}){2,}', s):
        s = s.replace('.', '')
    elif ',' in s:
        s = s.replace(',', '.')
    return float(s)


def _flatten_numbers(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _flatten_numbers(v)
    elif isinstance(obj, (int, float, Decimal)) and not isinstance(obj, bool):
        n = float(obj)
        if math.isfinite(n):
            yield n


def _metric_values(obj, field):
    """Trả về các giá trị theo tên trường, kể cả payload lồng nhau."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == field and isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
                n = float(v)
                if math.isfinite(n):
                    yield n
            elif isinstance(v, (dict, list)):
                yield from _metric_values(v, field)
    elif isinstance(obj, list):
        for v in obj:
            yield from _metric_values(v, field)


def _matches(a, b):
    return abs(a - b) <= max(0.02, abs(b) * 0.000001)


def _comparison_context(text, match):
    """Xác định MoM/YoY gắn với *chính* tỷ lệ đang xét.

    Giới hạn ngữ cảnh trước/sau ở tỷ lệ số kế bên và các liên từ
    tương phản để không gán nhầm YoY của tỷ lệ tiếp theo cho MoM.
    """
    before = text[max(0, match.start() - 180):match.start()]
    after = text[match.end():match.end() + 120]

    # Bỏ phần trước con số liền kề (vd 9.65 ... YoY giảm 10.91).
    previous_numbers = list(_TOKEN_PATTERN.finditer(before))
    if previous_numbers:
        before = before[previous_numbers[-1].end():]
    before = re.split(r'[!?;\n]|,\s*(?=trong\s+khi|còn|tuy\s+nhiên)',
                      before, flags=re.I)[-1]

    # Bỏ phần sau con số kế tiếp; không nhận nhãn thuộc tỷ lệ khác.
    next_number = _TOKEN_PATTERN.search(after)
    if next_number:
        after = after[:next_number.start()]
    after = re.split(r'[.!?;\n]|,\s*(?=trong\s+khi|còn|tuy\s+nhiên)',
                     after, maxsplit=1, flags=re.I)[0]

    before_labels = [(kind, found.end())
                     for kind, pattern in [('mom', _MOM), ('yoy', _YOY)]
                     for found in pattern.finditer(before)]
    after_labels = [(kind, found.start())
                    for kind, pattern in [('mom', _MOM), ('yoy', _YOY)]
                    for found in pattern.finditer(after)]

    # "so với tháng trước MoM tăng 9.65": nhãn ở trước số.
    # "giảm 17.26% so với cùng kỳ": nhãn ở sau số.
    if before_labels and not after_labels:
        return max(before_labels, key=lambda item: item[1])[0]
    if after_labels and not before_labels:
        return min(after_labels, key=lambda item: item[1])[0]
    if before_labels and after_labels:
        a = max(before_labels, key=lambda item: item[1])[0]
        b = min(after_labels, key=lambda item: item[1])[0]
        return a if a == b else None  # Ngữ cảnh mâu thuẫn: không tự cho PASS
    return None


def verify_claims(text, payload):
    """Kiểm tra số có trong nguồn và chiều biến động khi xác định được ngữ cảnh.

    FAIL nếu tỷ lệ không khớp MoM/YoY hoặc dấu mâu thuẫn với từ tăng/giảm.
    Không kiểm chứng nguyên nhân, quan hệ nhân quả hay đầy đủ ngữ nghĩa.
    """
    if not isinstance(text, str) or not text.strip():
        return False, 'AI không tạo nội dung'
    allowed = list(_flatten_numbers(payload))
    if not allowed:
        return False, 'JSON không chứa số KPI để đối chiếu'
    clean, bad_dates = _strip_and_check_dates(text, payload)
    if bad_dates:
        return False, 'Ngày/tháng không khớp JSON: ' + ', '.join(bad_dates[:12])
    matches = list(_TOKEN_PATTERN.finditer(clean))
    if not matches:
        return False, 'AI không dẫn chứng số KPI cụ thể'

    unknown = []
    for match in matches:
        token = match.group(0)
        try:
            n = _parse_number(token)
        except ValueError:
            unknown.append(token)
            continue

        following = clean[match.end():match.end() + 24]
        is_percent = bool(_PERCENT_SUFFIX.match(following))
        preceding = clean[max(0, match.start() - 80):match.start()]
        # Từ chỉ chiều phải đứng gần ngay trước trị số, không được có số
        # khác hoặc dấu kết thúc câu ở giữa.
        direction_match = _DIRECTION_PREFIX.search(preceding) if is_percent else None
        direction = None
        if direction_match:
            word = direction_match.group(1).lower()
            direction = -1 if word.startswith(('giảm', 'sụt', 'thấp')) else 1

        # Kiểm tra tỷ lệ đóng góp trước MoM/YoY. Tên nhóm gần nhất
        # trong cùng mệnh đề phải khớp chính giá trị của nhóm đó.
        if is_percent and isinstance(payload, dict):
            clause = re.split(r'[.!?;\n]', preceding)[-1]
            candidates = []
            for contributor in payload.get('contributors', []):
                if not isinstance(contributor, dict):
                    continue
                name = str(contributor.get('dimension_name') or '')
                value = contributor.get('contribution_pct_of_net_change')
                if not name or not isinstance(value, (int, float, Decimal)) or isinstance(value, bool):
                    continue
                for found in re.finditer(r'(?<!\w)' + re.escape(name) + r'(?!\w)', clause, re.I):
                    between = clause[found.end():]
                    if _TOKEN_PATTERN.search(between):
                        continue
                    # Xét cụm "Bikes với mức đóng góp 100%" hoặc "Southwest (15.5%)".
                    marker = bool(re.search(r'\b(?:đóng\s+góp|tỷ\s+trọng)\b', between, re.I))
                    parenthesis = bool(re.fullmatch(r'\s*\(\s*(?:đóng\s+góp\s*)?', between, re.I))
                    if marker or parenthesis:
                        candidates.append((found.end(), name, float(value)))
            if candidates:
                _, group_name, expected_contribution = max(candidates, key=lambda row: row[0])
                if not _matches(n, expected_contribution):
                    unknown.append(token + ' (đóng góp ' + group_name + ' không khớp)')
                continue

        if is_percent and direction is not None:
            if token.startswith('-') and direction > 0 or token.startswith('+') and direction < 0:
                unknown.append(token + ' (mâu thuẫn dấu/chiều)')
                continue
            expected = direction * abs(n)
            scope = _comparison_context(clean, match)
            if scope is None:
                # Không chấp nhận 'giảm x phần trăm' chung chung bằng việc
                # lấy tuyệt đối của một KPI bất kỳ.
                unknown.append(token + ' (không rõ MoM/YoY)')
                continue
            field = 'sales_mom_pct' if scope == 'mom' else 'sales_yoy_pct'
            values = list(_metric_values(payload, field))
            if not any(_matches(expected, v) for v in values):
                unknown.append(token + ' (' + scope.upper() + ' không khớp)')
            continue

        if is_percent and (direction is None):
            # Phần trăm với dấu rõ ràng vẫn phải khớp đúng KPI có ngữ cảnh.
            scope = _comparison_context(clean, match)
            if scope is not None:
                field = 'sales_mom_pct' if scope == 'mom' else 'sales_yoy_pct'
                values = list(_metric_values(payload, field))
                if not any(_matches(n, v) for v in values):
                    unknown.append(token + ' (' + scope.upper() + ' không khớp)')
                continue
        if not any(_matches(n, v) for v in allowed):
            unknown.append(token)

    if unknown:
        return False, 'Các số không đối chiếu được: ' + ', '.join(unknown[:12])
    return True, 'PASS: các số được nêu khớp input_json theo ngưỡng sai số cho phép'


SUMMARY_RULES = """Bạn là chuyên viên BI AdventureWorks. Viết bản tóm tắt KPI bằng tiếng Việt, tối đa 150 từ.
Chỉ dùng số trong JSON, không tự tạo số, không đoán nguyên nhân, không đưa khuyến nghị hành động.

Cấu trúc 3 đoạn, mỗi đoạn bắt đầu bằng nhãn (KHÔNG đánh số mục):
"Kết quả: " nêu doanh thu, lợi nhuận, số đơn hàng, AOV của kỳ.
"Xu hướng / đối chiếu: " nhận xét tăng hay giảm, mạnh hay nhẹ, dựa trên sales_mom_pct và
prior_month_sales có trong JSON, kèm đúng cụm 'so với tháng trước' ngay cạnh tỷ lệ. Nếu muốn
nhắc cùng kỳ năm trước, CHỈ nêu prior_year_sales dạng số tiền, KHÔNG viết tỷ lệ % YoY.
"Lưu ý: " nêu MỘT điểm cần kiểm tra thêm trên dashboard (kỳ thiếu đối chiếu, biến động lớn,
hoặc chỉ số cần theo dõi). Đây là gợi ý kiểm tra, không phải kết luận nguyên nhân.

QUY TẮC CHỐNG SUY DIỄN:
- Dẫn chứng ít nhất một KPI số; mỗi số đúng JSON, tối đa 2 chữ số thập phân.
- Viết số LIỀN, không phân nhóm hàng nghìn bằng dấu chấm/phẩy (viết 3029916.14, không viết 2.146).
- CHỈ nêu TỐI ĐA MỘT tỷ lệ % (sales_mom_pct), phải ghi rõ NGAY CẠNH số 'so với tháng trước'.
  Không viết tỷ lệ % YoY, không nối hai tỷ lệ % bằng 'và' / dấu phẩy / 'trong khi'.
- Không viết số ngoài JSON (kể cả số thứ tự), không đánh số mục.
- Cấm từ khẳng định nhân quả: 'do', 'vì', 'nhờ', 'nguyên nhân là', 'dẫn đến'.
- Nếu thiếu kỳ so sánh, nói đúng 'chưa có dữ liệu kỳ đối chiếu'."""

TREND_RULES = """Bạn là chuyên viên BI AdventureWorks. Giải thích biến động doanh thu bằng tiếng Việt, tối đa 160 từ.
Dùng ĐÚNG các số từ JSON, không bịa số, không đánh số mục.

Cấu trúc 3 đoạn, mỗi đoạn bắt đầu bằng nhãn:
"Biến động: " nêu mức thay đổi MoM của sales_amount, kèm kỳ và số cụ thể.
"Đóng góp: " nêu các nhóm có đóng góp lớn nhất. Khi nêu tỷ lệ đóng góp, phải kèm cụm
'đóng góp' hoặc 'tỷ trọng' ngay sau tên nhóm. Nếu tỷ lệ âm hoặc vượt 100%, nói rõ đây là
do các nhóm triệt tiêu nhau, không phải lỗi số liệu.
"Cần kiểm tra: " đưa MỘT gợi ý kiểm tra thêm trên dashboard (nhóm đối nghịch, kỳ bất thường,
hoặc chiều PRODUCT). Đây là gợi ý kiểm tra, KHÔNG khẳng định quan hệ nhân quả.

QUY TẮC CHỐNG SUY DIỄN:
- Chỉ xem phần đóng góp là BẰNG CHỨNG về mức tăng giảm, không khẳng định nguyên nhân.
- Cấm từ 'do', 'vì', 'nhờ', 'nguyên nhân là', 'dẫn đến'. Không dự báo, không khuyến nghị hành động.
- Chỉ nêu MỘT tỷ lệ % biến động (MoM), ghi rõ NGAY CẠNH số 'so với tháng trước'.
  Tỷ lệ đóng góp phải kèm cụm 'đóng góp'/'tỷ trọng' ngay sau tên nhóm; không viết % YoY.
- Không viết bất kỳ con số nào ngoài JSON (kể cả số thứ tự).
- Viết số LIỀN, không phân nhóm hàng nghìn bằng dấu chấm/phẩy (viết 3029916.14, không viết 2.146)."""
