   select
       p.product_key,
       p.product_sku,
       p.product_name,
       p.model_name,
       p.product_description,
       p.product_color,
       p.product_size,
       p.product_style,
       p.product_cost,
       p.product_price,
       coalesce(sc.subcategory_name, 'Unknown') as subcategory_name,
       coalesce(c.category_name, 'Unknown')     as category_name
   from {{ ref('stg_product') }} p
   left join {{ ref('stg_product_subcategory') }} sc
       on sc.product_subcategory_key = p.product_subcategory_key
   left join {{ ref('stg_product_category') }} c
       on c.product_category_key = sc.product_category_key