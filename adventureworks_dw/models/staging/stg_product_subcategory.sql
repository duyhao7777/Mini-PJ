   select
       cast(productsubcategorykey as int) as product_subcategory_key,
       trim(subcategoryname)              as subcategory_name,
       cast(productcategorykey as int)    as product_category_key
   from {{ source('stg', 'product_subcategory') }}