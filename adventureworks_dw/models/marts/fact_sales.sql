   select
       concat(s.order_number, '-', s.order_line_item)             as sales_line_id,
       cast(format(s.order_date, 'yyyyMMdd') as int)              as order_date_key,
       s.stock_date,
       s.product_key,
       s.customer_key,
       s.territory_key,
       s.order_number,
       s.order_line_item,
       s.order_quantity,
       s.order_quantity * p.product_price                         as sales_amount,
       s.order_quantity * p.product_cost                          as cost_amount,
       s.order_quantity * (p.product_price - p.product_cost)      as profit_amount,
       datediff(day, s.stock_date, s.order_date)                  as days_in_stock
   from {{ ref('stg_sales') }} s
   left join {{ ref('dim_product') }} p
       on p.product_key = s.product_key