{{ config(materialized='table', schema='ai') }}
with base as (
    select datefromparts(d.[year], d.month_number, 1) as month_start,
           f.order_number, f.order_quantity, f.sales_amount, f.profit_amount,
           cast(p.category_name as nvarchar(255)) as category_name,
           cast(p.product_name as nvarchar(255)) as product_name,
           cast(t.region as nvarchar(255)) as region_name,
           cast(f.product_key as nvarchar(255)) as product_key_txt,
           cast(f.territory_key as nvarchar(255)) as territory_key_txt
    from {{ ref('fact_sales') }} f
    inner join {{ ref('dim_date') }} d on d.date_key=f.order_date_key
    left join {{ ref('dim_product') }} p on p.product_key=f.product_key
    left join {{ ref('dim_territory') }} t on t.territory_key=f.territory_key
), grouped as (
    select month_start, 'CATEGORY' as dimension_type,
           coalesce(category_name, 'Unknown') as dimension_key,
           coalesce(category_name, 'Unknown') as dimension_name,
           order_number, order_quantity, sales_amount, profit_amount from base
    union all
    select month_start, 'TERRITORY', territory_key_txt,
           coalesce(region_name,'Unknown'), order_number, order_quantity, sales_amount, profit_amount from base
    union all
    select month_start, 'PRODUCT', product_key_txt,
           coalesce(product_name,'Unknown'), order_number, order_quantity, sales_amount, profit_amount from base
), monthly as (
    select month_start, dimension_type, dimension_key, max(dimension_name) as dimension_name,
           cast(sum(sales_amount) as decimal(19,2)) as sales_amount,
           cast(sum(profit_amount) as decimal(19,2)) as profit_amount,
           count(distinct order_number) as order_count,
           sum(order_quantity) as units_sold
    from grouped
    group by month_start,dimension_type,dimension_key
)
select c.month_start,c.dimension_type,c.dimension_key,c.dimension_name,
       c.sales_amount,c.profit_amount,c.order_count,c.units_sold,
       cast(c.sales_amount / nullif(c.order_count,0) as decimal(19,2)) as aov,
       coalesce(p.sales_amount,0) as prior_month_sales,
       cast(c.sales_amount-coalesce(p.sales_amount,0) as decimal(19,2)) as sales_mom_delta
from monthly c
left join monthly p on p.dimension_type=c.dimension_type and p.dimension_key=c.dimension_key
                   and p.month_start=dateadd(month,-1,c.month_start)
