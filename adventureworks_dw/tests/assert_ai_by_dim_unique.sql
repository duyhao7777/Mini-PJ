select month_start,dimension_type,dimension_key
from {{ ref('kpi_by_dim') }}
group by month_start,dimension_type,dimension_key
having count(*)>1
