UPDATE zsales_order
SET status = 'COMPLETED',
    changed_on = CURRENT_DATE
WHERE sales_order = '5000012345';

COMMIT;

INSERT INTO zsales_order_log (sales_order, action, created_on)
VALUES ('5000012345', 'UPDATED', CURRENT_DATE);
