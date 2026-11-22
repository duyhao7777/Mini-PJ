select b.month_start,b.dimension_type
from {{ ref('kpi_by_dim') }} b
join {{ ref('kpi_monthly') }} m on m.month_start=b.month_start
group by b.month_start,b.dimension_type,m.sales_amount
having abs(sum(b.sales_amount)-m.sales_amount)>0.05
