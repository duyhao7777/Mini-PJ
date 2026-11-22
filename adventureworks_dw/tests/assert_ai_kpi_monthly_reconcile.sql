select k.month_start
from {{ ref('kpi_monthly') }} k
join (
 select datefromparts(d.[year],d.month_number,1) month_start, sum(f.sales_amount) sales_amount
 from {{ ref('fact_sales') }} f join {{ ref('dim_date') }} d on f.order_date_key=d.date_key
 group by datefromparts(d.[year],d.month_number,1)
) x on k.month_start=x.month_start
where abs(k.sales_amount-x.sales_amount)>0.01
