   select
       cast(productcategorykey as int) as product_category_key,
       trim(categoryname)              as category_name
   from {{ source('stg', 'product_category') }}