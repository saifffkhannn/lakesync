-- Snowflake procedure to replicate ABAP UPDATE and INSERT operations
CREATE OR REPLACE PROCEDURE z_update_order_status()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    -- Update sales order status
    UPDATE zsales_order
    SET status = 'COMPLETED',
        changed_on = CURRENT_DATE
    WHERE sales_order = '5000012345';
    
    -- Insert audit log entry
    INSERT INTO zsales_order_log (
        sales_order,
        action,
        created_on
    )
    VALUES (
        '5000012345',
        'UPDATED',
        CURRENT_DATE
    );
    
    RETURN 'Order status update completed';
END;
$$;
