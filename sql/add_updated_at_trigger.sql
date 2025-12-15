-- Add automatic updated_at trigger for postings table
-- This ensures updated_at is set whenever ANY column is modified

-- Create the trigger function (reusable for any table)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to postings table
DROP TRIGGER IF EXISTS set_updated_at ON postings;

CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON postings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Test the trigger
SELECT 'Trigger created successfully!' as status;

-- Show current triggers on postings
SELECT 
    trigger_name,
    event_manipulation,
    action_timing
FROM information_schema.triggers
WHERE event_object_table = 'postings';
